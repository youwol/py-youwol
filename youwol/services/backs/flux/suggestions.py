import itertools
import pprint
from collections import defaultdict
from typing import NamedTuple

from models import Workflow, Module


class RowAssociation(NamedTuple):
    workflowId: str
    factoryIdStart: str
    packIdStart: str
    slotIdStart: str
    factoryIdEnd: str
    packIdEnd: str
    slotIdEnd: str


def get_leaf_module(start_module: Module, connections_dict):
    if start_module["module"].factoryId == "filter@flux-pack-flow-control":
        next_module = connections_dict[start_module.moduleId]
        get_leaf_module(next_module, connections_dict)

    return start_module


def get_connected_modules(project_id: str, module: Module, connections_dict):

    modules_to = [get_leaf_module(module, connections_dict) for module in connections_dict[module.moduleId]]

    rows = [RowAssociation(workflowId=project_id,
                           factoryIdStart=module.factoryId,
                           slotIdStart=m["inputSlotId"],
                           packIdStart=module.factoryId.split("@")[-1],
                           factoryIdEnd=m["module"].factoryId,
                           slotIdEnd=m["outputSlotId"],
                           packIdEnd=m["module"].factoryId.split("@")[-1])
            for m in modules_to]

    return rows


def get_suggestions_association(project_id: str, workflow: Workflow):

    modules = workflow.modules
    connections_to_dict = defaultdict(list)
    modules_dict = {m.moduleId: m for m in workflow.modules}
    for c in workflow.connections:
        connections_to_dict[c.outputSlot.moduleId].append({"inputSlotId": c.inputSlot.slotId,
                                                           "outputSlotId": c.outputSlot.slotId,
                                                           "module": modules_dict[c.inputSlot.moduleId]})

    modules_to = [get_connected_modules(project_id, m, connections_to_dict) for m in modules]
    rows = list(itertools.chain.from_iterable(modules_to))
    pprint.pprint(rows)
    return rows

#
# async def populate_docdb(project_id, storage, doc_db, auth):
#
#     workflow = await storage.get_json( path="flux-backend/projects/{}/workflow.json".format(project_id),
#                                        headers=await auth.headers())
#
#     associations = get_suggestions_association(project_id, Workflow(**workflow))
#     query = doc_db.query(kind=Config.kind_suggestions_assoc)
#     query.add_filter('workflowId', '=', project_id)
#     results = list(query.fetch())
#     doc_db.delete_multi([r.key for r in results])
#     keys = [ doc_db.key(Config.kind_suggestions_assoc) for row in associations ]
#     ds_rows = [ doc_db.Entity(key=key) for key in keys]
#     for i, row in enumerate(associations):
#         ds_rows[i].update({'workflowId': row.workflowId,
#                            'factoryIdStart': row.factoryIdStart,
#                            'slotIdStart': row.slotIdStart,
#                            'packIdStart': row.packIdStart,
#                            'factoryIdEnd': row.factoryIdEnd,
#                            'slotIdEnd': row.slotIdEnd,
#                            'packIdEnd': row.packIdEnd})
#     doc_db.put_multi(ds_rows)
#
# loop = get_event_loop()
# projects = loop.run_until_complete(populate_docdb("064c9ca8-cae6-4b89-b27d-274a58615bea"))
