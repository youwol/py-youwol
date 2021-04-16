import json
import sys
import base64
import glob
import itertools

"""
Most of it is most likely not needed anymore thanks to the cdn service.
Has to be cleaned.
"""


def getCdnUrl(namespace, name, version, cdnFilenameIds):
    default_path = "/api/cdn-backend/libraries/"
    if namespace:
        default_path += "{}/".format(namespace)
    default_path += "{}/{}/".format(name, version)

    if name in cdnFilenameIds and '/' in cdnFilenameIds[name]:
        return "/api/cdn-backend/libraries/" + cdnFilenameIds[name]
    if name in cdnFilenameIds:
        return default_path + cdnFilenameIds[name]

    return default_path + name + ".min.js"


def getExportId(name, umd_module_ids):
    export_id = [v for k, v in umd_module_ids.items() if name in k.split('/')]
    return name if len(export_id) == 0 else export_id[0]


def explicit_dependency(name, version, umd_module_ids):
    namespace = None
    r = {}
    r["id"] = name
    if '/' in name:
        namespace = name.split('/')[0]
        namespace = namespace[1:] if namespace[0] == '@' else namespace
        r["namespace"] = namespace
        name = name.split('/')[-1].strip('@')
    r["name"] = name
    r["version"] = version
    r["umdModuleId"] = getExportId(name, umd_module_ids)
    return r


def order_dependencies(dependencies, groups):
    r = []
    for d in dependencies:
        if "namespace" in d:
            r.append(d)
        else:
            r.insert(0, d)
    if (not groups):
        return r
    groups = [g if isinstance(g, list) else [g] for g in groups]
    flattened = list(itertools.chain.from_iterable(groups))

    def index(e):
        try:
            return flattened.index(e["id"])
        except:
            return len(flattened)

    r.sort(key=index)
    return r


def parse_package(filepath):
    r = {}
    with open(filepath, 'r') as file:
        jsonData = json.load(file)
        r["version"] = jsonData['version']

        r["id"] = jsonData["name"].split("/")[-1]
        r["fullname"] = jsonData["name"]
        r["name"] = jsonData["name"]

        if '/' in jsonData["name"]:
            namespace = jsonData["name"].split("/")[0]
            namespace = namespace[1:] if namespace[0] == '@' else namespace
            r["namespace"] = namespace

        r["displayName"] = jsonData["name"]
        r["description"] = jsonData["description"]
        r["author"] = jsonData["author"]
        r["tags"] = jsonData["keywords"]

        if "ngPackage" in jsonData and "assets" in jsonData["ngPackage"]:
            files = itertools.chain.from_iterable([glob.glob(pattern) for pattern in jsonData["ngPackage"]["assets"]])
            cssFiles = list([{
                "type": "css",
                "href": "/api/cdn-backend/libraries/youwol/{}/{}/{}".format(r["name"], r["version"], f)
                } for f in files if ".css" in f[-4:]])

    return r


parsed = parse_package("./package.json")
fullname = str(parsed["fullname"])
asset_raw_id = base64.urlsafe_b64encode(str.encode(fullname)).decode()

with open('src/auto-generated.ts', 'w') as file:
    file.write("// This file is auto-generated: do not edit \n")
    file.write("export const ASSET_ID = '{}' \n".format(asset_raw_id))
    if 'namespace' in parsed:
        file.write("export const NAMESPACE = '{}' \n".format(parsed["namespace"]))
    else:
        file.write("export const NAMESPACE = '' \n")
    file.write("export const NAME = '{}' \n".format(parsed["name"]))
    file.write("export const VERSION = '{}' \n".format(parsed["version"]))
    file.write("export const DESCRIPTION = '{}' \n".format(parsed["description"]))
    base_url = "/api/assets-gateway/raw/package/"+asset_raw_id+"/libraries/"+parsed['name'].replace('@', '')+"/"+parsed['version']
    file.write("export const URL_CDN = '{}' \n".format(base_url))

