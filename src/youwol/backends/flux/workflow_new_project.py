# Youwol utilities
from youwol.utils.http_clients.flux_backend import FactoryId, Module, Workflow

root_id = "root-component"
# noinspection SpellCheckingInspection
html = f"""
<div id='Component_{root_id}' class='flux-element flux-component' data-gjs-name='{root_id}'>
    <div class='d-flex flex-column justify-content-around text-center h-100 fv-bg-background fv-text-primary'
    data-gjs-name='welcome-page' >
        <img is="fv-img" width='250px' class="mx-auto" data-gjs-name='youwol-logo' src="/api/assets-gateway/raw/package/
QHlvdXdvbC9mbHV4LXlvdXdvbC1lc3NlbnRpYWxz/latest/assets/images/logo_YouWol_Platform_white.png" style="width: 250px;">
        <span data-gjs-name='welcome-sentence'> Hi YouWol </span>
        <div class='mx-auto text-left mx-auto border rounded p-5 fv-color-primary' data-gjs-name='useful-links'>
            <span data-gjs-name='useful-links-header'> A couple of useful links: </span>
            <ul data-gjs-name='useful-links-items'>
                <li> <a href=''>Getting started video </a> </li>
                <li> <a href=''>Getting started tutorial</a> </li>
            </ul>
        </div>
    </div>
</div>
"""
css = f"""#Component_{root_id}{{
    width: 100%;
    height: 100%;
    padding: 15px
}}"""

workflow_new_project = Workflow(
    modules=[
        Module(
            configuration={
                "title": "Root component",
                "description": "This is the root component",
                "data": {"html": html, "css": css},
            },
            moduleId="Component_root-component",
            factoryId=FactoryId(module="Component", pack="@youwol/flux-core"),
        )
    ],
    connections=[],
)
