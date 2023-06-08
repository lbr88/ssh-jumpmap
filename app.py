import os
import re
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network

CONFIG_FILE = os.path.expanduser("~/.ssh/config")


import glob


def parse_ssh_config(file_path, parse_includes=True):
    hosts = {}

    with open(file_path, "r") as file:
        lines = file.readlines()

    current_host = None
    for line in lines:
        line = line.strip()

        if line.startswith("Include "):
            include_pattern = line.split(" ")[1]
            # Resolving relative paths
            if not include_pattern.startswith("/") and not include_pattern.startswith(
                "~"
            ):
                include_pattern = os.path.join(
                    os.path.dirname(file_path), include_pattern
                )
            include_pattern = os.path.expanduser(include_pattern)

            include_paths = glob.glob(include_pattern)
            for include_path in include_paths:
                include_hosts = parse_ssh_config(include_path)
                hosts.update(include_hosts)

        elif line.startswith("Host "):
            all_current_hosts = line.split(" ")
            current_host = all_current_hosts[1]
            if len(all_current_hosts) == 1:
                hosts[current_host] = {"Host": current_host}
            else:
                additional_current_hosts = all_current_hosts[2:]
                hosts[current_host] = {
                    "Host": current_host,
                    "AdditionalHosts": additional_current_hosts,
                }

        elif line.startswith("ProxyJump "):
            proxy_jump = line.split(" ")[1]
            proxy_jump_list = proxy_jump.split(",")
            last_proxy_jump = None
            for jump in proxy_jump_list:
                if last_proxy_jump:
                    if last_proxy_jump not in hosts:
                        hosts[last_proxy_jump] = {"Host": last_proxy_jump}
                    hosts[last_proxy_jump]["ProxyJump"] = jump
                last_proxy_jump = jump
            hosts[current_host]["ProxyJump"] = last_proxy_jump
    return hosts


def create_graph(hosts, remove_wildcards=False):
    graph = nx.Graph()

    for host, attributes in hosts.items():
        if "*" in host and host != "*":
            match = host.replace("*", ".+")
            wildhosts = [h for h in hosts if re.match(match, h)]
            for h in wildhosts:
                # skip self
                if h == host or attributes.get("ProxyJump") == h or h == "*":
                    continue
                graph.add_node(host, **attributes)
                print(f"adding {host}")
                if "ProxyJump" in attributes:
                    graph.add_edge(attributes["ProxyJump"], host)
                    print(f"adding edge {attributes['ProxyJump']} -> {host}")
                # print(host, h)
            if h in graph:
                graph.remove_node(h)
                print(f"removing {h}")
        else:
            if host not in graph:
                graph.add_node(host)
                print(f"adding {host}")

            if "ProxyJump" in attributes:
                graph.add_edge(attributes["ProxyJump"], host)
                print(f"adding edge {attributes['ProxyJump']} -> {host}")

    # if set go through all nodes and remove nodes that are matched by a wildcard
    if remove_wildcards:
        cleanup_graph = graph.copy()
        for node in cleanup_graph.nodes:
            if "*" in node and node != "*":
                match = node.replace("*", ".+")
                wildhosts = [h for h in graph.nodes if re.match(match, h)]
                for h in wildhosts:
                    if h == node:
                        continue
                    print(f"removing {h} matched by {node}")
                    graph.remove_node(h)

    return graph


import math


def draw_graph(graph, center_localhost=False):
    # k = 5 / math.sqrt(graph.order())
    # graph = graph.reverse()
    # pos = nx.spring_layout(graph, iterations=50)
    # pos = nx.(graph, iterations=50)
    # pos = nx.kamada_kawai_layout(graph)
    # if center_localhost:
    #    pos["localhost"] = [0, 0]
    #    nx.draw(graph, pos, with_labels=False)
    # nx.draw(graph, pos, with_labels=True, font_size=8)
    # edge_labels = nx.get_edge_attributes(graph, "ProxyJump")
    # nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
    nt = Network("1000px", "1800px")
    nt.from_nx(graph)
    nt.toggle_physics(True)
    nt.show("nx.html", notebook=False)
    # plt.show()


def anonimize_hosts(hosts):
    import hashlib

    hosts_anon = {}
    node_names = {}
    for host, attributes in hosts.items():
        host_parts = host.split("_")
        host_name = (
            hashlib.sha256(host_parts[0].encode()).hexdigest()[:8]
            + "_"
            + "_".join(host_parts[1:])
        ).rstrip("_")
        node_names[host_name] = host.rstrip("_")
        hosts_anon[host_name] = {}
        for key, value in attributes.items():
            if key == "ProxyJump":
                proxy_jump_parts = value.split("_")
                proxy_jump_name = (
                    hashlib.sha256(proxy_jump_parts[0].encode()).hexdigest()[:8]
                    + "_"
                    + "_".join(proxy_jump_parts[1:])
                ).rstrip("_")
                node_names[proxy_jump_name] = value
                hosts_anon[host_name][key] = proxy_jump_name
            else:
                hosts_anon[host_name][key] = value
    return hosts_anon


import hashlib
import argparse

if __name__ == "__main__":
    # TODO: add command line arguments

    # "Settings
    # Anon anonymize hostnames
    Anon = False
    # remove_wildcards remove nodes that are matched by a wildcard
    remove_wildcards = False
    # AddLocalhost add localhost and connect it to all nodes that are not connected
    AddLocalhost = True
    hosts = parse_ssh_config(CONFIG_FILE)
    if Anon:
        hosts = anonimize_hosts(hosts)
    graph = create_graph(hosts, remove_wildcards=remove_wildcards)

    if AddLocalhost:
        graph.add_node("localhost")
        for node, attributes in graph.nodes(data=True):
            print(node, attributes)
            # if len(graph.edges(host)):
            if not attributes.get("ProxyJump"):
                graph.add_edge("localhost", node)
        # for host, attributes in hosts.items():
        #    if len(graph.edges(host)) > 0:
        #        # if not attributes.get("ProxyJump"):
        #        graph.add_edge("localhost", host)

    # print all nodes and their edges
    for node in graph.nodes:
        print(node, graph.edges(node))

    print(graph)
    draw_graph(graph, center_localhost=False)
