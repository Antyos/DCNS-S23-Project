from __future__ import annotations

import asyncio
import socket
import tempfile
from datetime import timedelta
from json import dumps
from os import remove
from os.path import dirname
from os.path import join as pathjoin
from random import randint
from time import sleep
from typing import Iterable, Optional
from webbrowser import open_new

import tornado.httpserver
import tornado.httputil
import tornado.ioloop
import tornado.web
import tornado.websocket
from networkx import DiGraph, Graph
from typing_extensions import NotRequired, TypedDict

from .d3graph import EDGE_INDEX, NODE_INDEX, D3DiGraph, D3Graph, Edge, Node

__all__ = ["create_d3nx_visualizer", "D3NetworkxRenderer"]

visualizer_clients = []
websocket_clients = []
messages_todo = []


class GraphNotSetError(Exception):
    ...


class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.set_nodelay(True)
        if self not in websocket_clients:
            websocket_clients.append(self)
        # print('new connection @ '+str(self))

    def on_message(self, message):
        # print('message received @ %s:  %s' % (str(self),message))
        if message == "visualizer":
            visualizer_clients.append(self)
            print("visualizer connected...", end="")
        elif message == "python":
            print("networkx connected...", end="")
        else:
            self.send_to_visualizers(message)
            # self.write_message('1')

    def send_to_visualizers(self, message):
        for c in visualizer_clients:
            c.write_message(message)

    def on_close(self):
        if self in websocket_clients:
            websocket_clients.remove(self)
        if self in visualizer_clients:
            visualizer_clients.remove(self)
        # print('connection closed @ '+str(self))

    def check_origin(self, origin):
        return True


_STYLE_SHAPE = "shape"
_STYLE_SIZE = "size"
_STYLE_FILL = "fill"
_STYLE_STROKE = "stroke"
_STYLE_STROKE_WIDTH = "strokewidth"


class NodeStyle(TypedDict):
    shape: NotRequired[str]
    size: NotRequired[float]
    fill: NotRequired[str]
    stroke: NotRequired[str]
    strokewidth: NotRequired[float]


class EdgeStyle(TypedDict):
    stroke: NotRequired[str]
    strokewidth: NotRequired[float]


def node_style(
    shape="circle",
    size: float = 8,
    fill="#77BEF5",
    stroke="#FFFFFF",
    stroke_width: float = 2,
) -> NodeStyle:
    return {
        _STYLE_SHAPE: shape,
        _STYLE_SIZE: size,
        _STYLE_FILL: fill,
        _STYLE_STROKE: stroke,
        _STYLE_STROKE_WIDTH: stroke_width,
    }


def edge_style(stroke="#494949", stroke_width: float = 2) -> EdgeStyle:
    return {
        _STYLE_STROKE: stroke,
        _STYLE_STROKE_WIDTH: stroke_width,
    }


async def create_d3nx_visualizer(
    event_delay=0.03,
    interactive=True,
    canvas_size: tuple[int, int] = (800, 600),
    autolaunch=True,
    port: Optional[int] = None,
    node_dstyle: Optional[NodeStyle] = None,
    edge_dstyle: Optional[EdgeStyle] = None,
    node_hstyle: Optional[NodeStyle] = None,
    edge_hstyle: Optional[EdgeStyle] = None,
):
    if port is None:
        port = 5000 + randint(1, 4999)

    tmpname = None
    if autolaunch:
        # print('launching visualizer!')
        p = pathjoin(
            f"file://{dirname(__file__)}",
            f"visualizer.html?width={canvas_size[0]}&height={canvas_size[1]}&port={port}",
        ).replace("\\", "/")
        # Need a temporary redirect to open local html with query params
        # https://stackoverflow.com/q/72553727
        # Ideally, we would set the context manager to delete the file at the end, but
        # the webbrowser doesn't know what to do if we try to call open_new() from
        # within the context manager.
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(f'<meta http-equiv="refresh" content="0; URL={p}" />')
            tmpname = f.name

        open_new(f"file://{tmpname}")

    d3 = D3NetworkxRenderer(
        event_delay=event_delay,
        interactive=interactive,
        port=port,
        node_dstyle=node_dstyle,
        edge_dstyle=edge_dstyle,
        node_hstyle=node_hstyle,
        edge_hstyle=edge_hstyle,
    )

    await d3.start_client()
    assert d3.client is not None
    d3.client.write_message("python")
    d3.start_client_polling()

    if tmpname is not None:
        sleep(1)
        remove(tmpname)

    return d3


class D3NetworkxRenderer(object):
    MAGICKEY = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(
        self,
        event_delay=0.03,
        interactive=True,
        port=9876,
        node_dstyle=None,
        edge_dstyle=None,
        node_hstyle=None,
        edge_hstyle=None,
    ):
        self.event_delay = event_delay
        self.port = port
        self.server = None
        self.client = None
        self.interactive = interactive

        self.default_node_style: NodeStyle = node_dstyle or node_style()
        self.default_edge_style: EdgeStyle = edge_dstyle or edge_style()
        self.highlighted_node_style = node_hstyle or node_style(size=10, fill="#FD5411")
        self.highlighted_edge_style = edge_hstyle or edge_style(
            stroke="#F79C00", stroke_width=4
        )
        self._highlighted_nodes = set()
        self._highlighted_edges = set()

        self.updates_todo = []

        self.start_server()

    def set_graph(self, graph: D3Graph | D3DiGraph):
        self.clear()
        if graph is None:
            return
        self._graph = graph
        self._directed = isinstance(graph, DiGraph)
        self._graph.add_listener(self)

        # Add nodes and edges if graph already has them
        if self._graph.number_of_nodes() > 0:
            for n in self._graph.nodes():
                self.node_added(self._graph.node_index(n), n, self._graph.nodes[n])
            for u, v, *_ in self._graph.edges():
                self.edge_added(*self._graph.edge_indices(u, v), self._graph[u][v])

    def set_title(self, newtitle: str):
        ti = {"titlename": newtitle}
        self._send_update(f"ti{dumps(ti)}")
        self.update()

    def clear(self):
        self.clear_highlights()
        self._graph = None
        self._send_update("cc")
        self.update()

    def update(self):
        self._send_update("up")

    def set_event_delay(self, delay: float):
        self.event_delay = delay

    def set_interactive(self, interactive: bool):
        self.interactive = interactive

    # Setting the position of nodes
    def position_node(self, n: Node, x: float, y: float):
        if self._graph is None:
            raise GraphNotSetError
        mv_node = {"nid": self._graph.node_index(n), "fixed": True, "cx": x, "cy": y}
        self._send_update(f"mn{dumps(mv_node)}")

    # data is a list of tuples with form (node_object, x, y)
    def position_nodes(self, data):
        for n, x, y in data:
            self.position_node(n, x, y)

    # Adding style to nodes
    def stylize_node(self, n: Node, style_dict: NodeStyle):
        if self._graph is None:
            raise GraphNotSetError
        self._send_update(
            f"!n{self._node_update(self._graph.node_index(n), n, style_dict)}"
        )

    def stylize_nodes(self, nodes: Iterable[Node], style_dict: NodeStyle):
        for n in nodes:
            self.stylize_node(n, style_dict)

    # Adding style to edges
    def stylize_edge(self, u: Node, v: Node, style_dict: EdgeStyle):
        if self._graph is None:
            raise GraphNotSetError
        self._send_update(
            f"!e{self._edge_update(*self._graph.edge_indices(u, v), style_dict)}"
        )

    def stylize_edges(self, ebunch: Iterable[Edge], style_dict: EdgeStyle):
        for e in ebunch:
            self.stylize_edge(*e, style_dict)

    # Automatically called, do not call directly
    def node_added(self, nidx: int, n: Node, data: dict):
        self._send_update(f"+n{self._node_update(nidx, n)}")

    # Automatically called, do not call directly
    def node_removed(self, nidx: int, n: Node):
        rm_node = {"nid": nidx}
        self._send_update(f"-n{dumps(rm_node)}")

    # Automatically called, do not call directly
    def edge_added(self, eidx: int, uidx: int, vidx: int, data: dict):
        self._send_update(f"+e{self._edge_update(eidx, uidx, vidx)}")

    # Automatically called, do not call directly
    def edge_removed(self, eidx: int, uidx: int, vidx: int):
        rm_edge = {"eid": eidx}
        self._send_update(f"-e{dumps(rm_edge)}")

    # Highlighting Nodes
    def highlight_nodes(self, nodes: Iterable[Node]):
        self.stylize_nodes(nodes, self.highlighted_node_style)
        self._highlighted_nodes.update(set(nodes))

    def highlight_nodes_by_index(self, nidxs: Iterable[int]):
        if self._graph is None:
            raise GraphNotSetError
        self.highlight_nodes([self._graph.node_by_index(nidx) for nidx in nidxs])

    def highlight_edges(self, edges: Iterable[Edge]):
        self.stylize_edges(edges, self.highlighted_edge_style)
        self._highlighted_edges.update(set(edges))

    def clear_highlights(self):
        self.stylize_nodes(self._highlighted_nodes, self.default_node_style)
        self.stylize_edges(self._highlighted_edges, self.default_edge_style)
        self._highlighted_nodes = set()
        self._highlighted_edges = set()

    # Helper functions for sending updates
    def _node_update(self, nidx, nobj, style_dict: Optional[NodeStyle] = None):
        if style_dict is None:
            style_dict = {}
        update_node = {"nid": nidx, "ntitle": ""}
        if nobj is not None:
            update_node["ntitle"] = str(nobj)
        final_style = self.default_node_style.copy()
        final_style.update(style_dict)
        update_node.update(final_style)
        return dumps(update_node)

    def _edge_update(self, eidx, uidx, vidx, style_dict: Optional[EdgeStyle] = None):
        if style_dict is None:
            style_dict = {}
        update_edge = {
            "source": uidx,
            "target": vidx,
            "eid": eidx,
            "directed": int(self._directed),
        }
        final_style = self.default_edge_style.copy()
        final_style.update(style_dict)
        update_edge.update(final_style)
        return dumps(update_edge)

    def _send_update(self, update=None):
        if update is not None:
            self.updates_todo.append(update)
            # print('Appended to the todo: '+update)
            if self.interactive:
                self.updates_todo.append("up")

    def _write_update(self):
        if self.client is None or asyncio.isfuture(self.client):
            print("NetworkX client is still loading.")
            return

        while len(self.updates_todo) > 0:
            update = self.updates_todo.pop(0)
            self.client.write_message(update)
            # print('Client Wrote: '+update)
            if update == "up":
                break
        tornado.ioloop.IOLoop.current().add_timeout(
            timedelta(milliseconds=int(self.event_delay * 1000)), self._write_update
        )

        # msg = yield self.client.read_message()
        # print('got back after up: '+msg)
        # sleep(self.event_delay)
        # asyncio.sleep(self.event_delay)

    def start_server(self):
        application = tornado.web.Application([(r"/ws", WSHandler), (r"/", WSHandler)])
        self.server = tornado.httpserver.HTTPServer(application)
        self.server.listen(self.port, "127.0.0.1")
        myIP = socket.gethostbyname(socket.gethostname())
        print("websocket server started...", end="")  #' at %s***' % myIP)

    def stop_server(self):
        assert self.server is not None
        self.server.stop()

    async def start_client(self):
        self.client = await tornado.websocket.websocket_connect(
            f"ws://localhost:{self.port}/ws"
        )

    def start_client_polling(self):
        tornado.ioloop.IOLoop.current().add_timeout(
            timedelta(milliseconds=int(self.event_delay * 1000)), self._write_update
        )
