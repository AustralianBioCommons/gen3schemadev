import json, requests, os, argparse
from gen3.submission import Gen3Error

"""
Code adapted from @cgmeyer here: https://github.com/cgmeyer/gen3sdk-python/blob/master/expansion/delete_uploaded_files.py
Takes as input a file manifest downloaded from Gen3 and deletes all files contained in it 
"""


def parse_args():
    global args
    parser = argparse.ArgumentParser(description="Delete unmapped files uploaded with the gen3-client.")
    parser.add_argument("-a", "--api", help="The data commons URL.", default="https://data.acdc.ozheart.org")
    parser.add_argument("-f", "--file-manifest", required=True, help="File manifest from Gen3 containing the files that "
                                                                     "need to be deleted")
    parser.add_argument("-c", "--creds", default="_local/credentials.json",
                        help="The location of the credentials.json file containing the user's API keys downloaded from "
                             "the /profile page of the commons.")
    args = parser.parse_args()
    return args


def get_token():
    global token
    with open(args.creds, 'r') as f:
        credentials = json.load(f)
    token_url = "{}/user/credentials/api/access_token".format(args.api)
    resp = requests.post(token_url, json=credentials)
    if (resp.status_code != 200):
        raise(Exception(resp.reason))
    token = resp.json()['access_token']
    return token

def delete_uploaded_files(guids):
    """ Deletes all locations of a stored data file and remove its record from indexd.
    """
    headers = {'Authorization': 'bearer ' + get_token()}
    if isinstance(guids, str):
        guids = [guids]

    if not isinstance(guids, list):
        raise Gen3Error("Please, supply GUIDs as a list.")

    for guid in guids:
        fence_url = "{}/user/data/".format(args.api)
        try:
            response = requests.delete(fence_url + guid,headers=headers)
        except requests.exceptions.ConnectionError as e:
            raise Gen3Error(e)

        if (response.status_code == 204):
            print("Successfully deleted GUID {}".format(guid))

        elif (response.status_code == 500):
            # delete from indexd endpoint
            index_url = "{}/index/index/{}".format(args.api,guid)
            response = requests.get(index_url)
            irec = json.loads(response.text)
            rev = irec['rev']
            index_url = "{}/index/index/{}?rev={}".format(args.api,guid,rev)
            try:
                response = requests.delete(index_url, headers=headers)
            except requests.exceptions.ConnectionError as e:
                raise Gen3Error(e)
            if response.status_code == 200:
                print("\tSuccessfully deleted GUID {}".format(guid))

        else:
            print("Error deleting GUID {}:".format(guid))
            print(response.reason)


if __name__ == "__main__":
    args = parse_args()
    manifest_path = os.path.expanduser(args.file_manifest)
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    guids = [x['object_id'].split("/")[1] for x in manifest]
    print("Parsed the following guids for deletion: {}".format(guids))
    delete_uploaded_files(guids)
