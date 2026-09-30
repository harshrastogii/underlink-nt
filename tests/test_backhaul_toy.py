"""Dominators on small graphs where the answer is known by hand."""
import networkx as nx
import pandas as pd

from underlink import network as nw


def toy(edges, roots, isolated=()):
    G = nx.Graph(edges)
    G.add_nodes_from(isolated)
    sites = pd.DataFrame({"site_key": list(G.nodes)}).set_index("site_key", drop=False)
    return nw.Network(G=G, sites=sites, anchors=pd.DataFrame(), roots=set(roots))


def test_chain_every_relay_is_single_point():
    # S is fibre-connected. S - a - b - c: a and b have no alternative.
    net = toy([("S", "a"), ("a", "b"), ("b", "c")], roots={"S"})
    idom = nw.dominator_tree(net)
    assert nw.chain_of("c", idom, net.roots) == ["b", "a"]
    assert nw.chain_of("a", idom, net.roots) == []


def test_diamond_has_no_single_point_inside_the_loop():
    # S - p, then two paths p-q1-r and p-q2-r, then r - t.
    net = toy([("S", "p"), ("p", "q1"), ("p", "q2"), ("q1", "r"), ("q2", "r"), ("r", "t")], roots={"S"})
    idom = nw.dominator_tree(net)
    assert nw.chain_of("t", idom, net.roots) == ["r", "p"]
    assert nw.chain_of("r", idom, net.roots) == ["p"]      # q1 and q2 back each other up


def test_roots_are_excluded():
    # Two fibre-connected sites in a row: the one between is fibre, not a relay.
    net = toy([("S1", "S2"), ("S2", "a"), ("a", "b")], roots={"S1", "S2"})
    idom = nw.dominator_tree(net)
    assert nw.chain_of("b", idom, net.roots) == ["a"]


def test_second_fibre_town_removes_the_single_point():
    # a - b - c with fibre at both ends: b has two ways out.
    net = toy([("S1", "a"), ("a", "b"), ("b", "c"), ("c", "S2")], roots={"S1", "S2"})
    idom = nw.dominator_tree(net)
    assert nw.chain_of("b", idom, net.roots) == []


def test_classify_all_four_classes():
    net = toy([("S", "a"), ("a", "b"), ("x", "y")], roots={"S"})
    places = pd.DataFrame({"place_key": ["P1", "P2", "P3", "P4"], "end_site": ["S", "b", "y", None]})
    out = nw.classify(places, net).set_index("place_key")
    assert out.chain_class.to_dict() == {"P1": "at-anchor", "P2": "radio-chain", "P3": "radio-island", "P4": "no-radio-site"}
    assert out.loc["P2", "spof_relays"] == ["a"]
    assert out.loc["P2", "hops"] == 2


def test_removing_a_relay_cuts_the_place():
    net = toy([("S", "a"), ("a", "b")], roots={"S"})
    places = pd.DataFrame({"place_key": ["P1"], "end_site": ["b"]})
    assert nw.classify(places, net, removed={"a"}).chain_class.iloc[0] == "radio-island"
