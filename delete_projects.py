"""Script to delete projects using their project names"""

import argparse
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
from gen3.index import Gen3Index
import requests
import os
import json
import sys
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects", nargs="*", required=True,
                        help="The names of the specific projects to delete.")
    parser.add_argument("--profile", action="store", required=True,
                        help="The name of your gen3-client profile that is configured with authorisation to delete.")
    parser.add_argument("--credentials-path", action="store", default="_local/credentials.json",
                        help="The name of your gen3-client profile that is configured with authorisation to delete.")
    parser.add_argument("--numparallel", action="store", default=2,
                        help="how many cores to use for uploading in parallel")
    return parser.parse_args()


def get_submission_order(
        sub_obj,
        root_node="project",
        excluded_schemas=[
            "_definitions",
            "_settings",
            "_terms",
            "program",
            "project",
            "root",
            "data_release",
            "metaschema",
        ]):
    """
    This function gets a data dictionary, and then it determines the submission order of nodes by looking at the links.
    The reverse of this is the deletion order for deleting projects. (Must delete child nodes before parents).
    Adapted from @cgmeyer https://github.com/cgmeyer/gen3sdk-python/blob/a089f36b747dd2182c9ed4eefb07471003c1e41c/expansion/expansion.py#L1008
    """
    dd = sub_obj.get_dictionary_all()
    schemas = list(dd)
    nodes = [k for k in schemas if k not in excluded_schemas]
    submission_order = [
        (root_node, 0)
    ]  # make a list of tuples with (node, order) where order is int
    while (
            len(submission_order) < len(nodes) + 1
    ):  # "root_node" != in "nodes", thus the +1
        for node in nodes:
            if (
                    len([item for item in submission_order if node in item]) == 0
            ):  # if the node != in submission_order
                # print("Node: {}".format(node))
                node_links = dd[node]["links"]
                parents = []
                for link in node_links:
                    if "target_type" in link:  # node = 'webster_step_second_test'
                        parents.append(link["target_type"])
                    elif "subgroup" in link:  # node = 'expression_array_result'
                        sub_links = link.get("subgroup")
                        if not isinstance(sub_links, list):
                            sub_links = [sub_links]
                        for sub_link in sub_links:
                            if "target_type" in sub_link:
                                parents.append(sub_link["target_type"])
                if False in [
                    i in [i[0] for i in submission_order] for i in parents
                ]:
                    continue  # if any parent != already in submission_order, skip this node for now
                else:  # submit this node after the last parent to submit
                    parents_order = [
                        item for item in submission_order if item[0] in parents
                    ]
                    submission_order.append(
                        (node, max([item[1] for item in parents_order]) + 1)
                    )
    return submission_order


def delete_project(project_id, sub_obj, root_node="project", program="program1", chunk_size=200):
    """
    Adapted from @cgmeyer: https://github.com/cgmeyer/gen3sdk-python/blob/a089f36b747dd2182c9ed4eefb07471003c1e41c/expansion/expansion.py#L1065
    """
    submission_order = get_submission_order(sub_obj, root_node=root_node)
    delete_order = sorted(submission_order, key=lambda x: x[1], reverse=True)
    nodes = [i[0] for i in delete_order]
    try:
        nodes.remove("project")
    except:
        print("No 'project' node in list of nodes.")
    data = sub_obj.delete_nodes(program, project_id, nodes, batch_size=chunk_size)
    try:
        data = sub_obj.delete_project(program=program, project=project_id)
    except Exception as e:
        print("Couldn't delete project '{}':\n\t{}".format(project_id, e))
    if "Can not delete the project." in data:
        print("{}".format(data))
    else:
        print("Successfully deleted the project '{}'".format(project_id))


if __name__ == "__main__":
    args = parse_arguments()
    endpoint = "https://data.acdc.ozheart.org"
    auth = Gen3Auth(endpoint=endpoint, refresh_file="_local/credentials.json")
    sub = Gen3Submission(endpoint=endpoint, auth_provider=auth)
    for project in args.projects:
        delete_project(project, sub)


