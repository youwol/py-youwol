# Youwol backends
from youwol.backends.flux.configurations import Constants

# Youwol utilities
from youwol.utils.http_clients.flux_backend import (
    DeprecatedData,
    FactoryId,
    Module,
    Project,
)


def from_0_to_1(project: Project, deprecated_data: DeprecatedData):
    """
    This conversion handle:
    * Before: the tree structure of the project was in a tree structure 'rootLayerTree', html & css were not
     encapsulated by layer; there were contained in 'project.runnerRendering'
    * After: there is no more 'layerTree' data, the tree structure of the project is encapsulated within Group and
    Components. Html & css are encapsulated by the Components.

    At the time when the migration from '0' to '1' happened, applications were not supposed to have children Components.
    The patch is about:
    * adding a 'root-component' to the project, encapsulating the all html and css.
    * transfer 'moduleIds' stored in the 'layerTree' to the associated GroupModules
    """
    root_id = "Component_root-component"
    root_component = Module(
        moduleId=root_id,
        configuration={
            "title": "Root component",
            "description": "This is the root component",
            "data": {
                "explicitInputsCount": 0,
                "explicitOutputsCount": 0,
                "css": project.runnerRendering.style,
                "html": f"""<div id='{root_id}' class='flux-element flux-component p-2'>
{project.runnerRendering.layout}</div>""",
                "moduleIds": deprecated_data.rootLayerTree["moduleIds"],
                "environment": "return {}",
            },
        },
        factoryId=FactoryId(module="Component", pack="@youwol/flux-core"),
    )
    project.workflow.modules.append(root_component)

    group_modules = [
        module
        for module in project.workflow.modules
        if module.factoryId.module == "GroupModules"
        and module.factoryId.pack == "@youwol/flux-core"
    ]

    def get_layers_data_recursive(acc, layer):
        if not layer["children"]:
            return acc
        data = {
            **acc,
            **{
                "GroupModules_" + child["layerId"]: child["moduleIds"]
                for child in layer["children"]
            },
        }
        for child_layer in layer["children"]:
            data = get_layers_data_recursive(data, child_layer)
        return data

    all_layers = get_layers_data_recursive({}, deprecated_data.rootLayerTree)
    for group in group_modules:
        group.configuration["data"]["moduleIds"] = all_layers[group.moduleId]

    project.schemaVersion = "1"
    return project


compatibilities_factory = {"0": from_0_to_1}


def convert_project_to_current_version(
    project: Project, deprecated_data: DeprecatedData
):
    if project.schemaVersion == Constants.current_schema_version:
        return project

    def apply_conversion(from_project: Project):
        if from_project.schemaVersion == Constants.current_schema_version:
            return from_project
        next_project_version = compatibilities_factory[from_project.schemaVersion](
            project, deprecated_data
        )
        return apply_conversion(from_project=next_project_version)

    apply_conversion(from_project=project)

    return project
