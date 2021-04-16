## Abstract

This is a skeleton package created using the flux-pack pipeline. 
This readme and the code documentation helps to get started with the construction
of a flux-pack. 
If you are already familiar with the concepts you can just remove all of this 
and start your package.

> This documentation is written like a tutorial with all the source code already included.
> If you are running the dashboard you can *build>test>publish* the resource and directly 
> create a flux-app using the modules. Do not hesitate to add or modify stuffs from the source and 
> see how it goes in your browser. 

[test0][ref_test0_wf]

## Tutorial

### Step 1: declaring the flux pack

This is the first step, you need to expose your new package. 

[[ pack | Declaring the flux pack ]].

### Step 2: a simple module case

In this part we present the definition of a module that does 'computation':
it takes some input, a couple of configuration parameters, 
and send back some results in its output. 

[[ Example0 | A simple module case ]].



## Commands 

While the local environment dashboard should allow you to not worry 
about the following commands, it is still good to know they exist.
Also, at some point, you may want to directly use them through a terminal rather 
than using the dashboard.

To install the required dependencies:
```shell
yarn 
```
To build for development:
```shell
yarn build:dev
```
To build for production:
```shell
yarn build:prod
```
Building for production will also build the documentation.

To test:
```shell
yarn test
```

## About dependencies management: CDN or not CDN

We need to discuss here about dependencies management, in particular
what kind of benefits/drawbacks the YouWol's CDN provides.


[ref_test0_wf]: </ui/flux-ui-builder/?uri=%7B%22name%22%3A%22new%20flux-project%22%2C%22description%22%3A%22%22%2C%22requirements%22%3A%7B%22fluxComponents%22%3A%5B%5D%2C%22fluxPacks%22%3A%5B%22%40youwol%2Fflux-files%22%2C%22%40youwol%2Fflux-pack-utility-std%22%5D%2C%22libraries%22%3A%7B%22%40youwol%2Fflux-files%22%3A%220.0.0%22%2C%22%40youwol%2Ffv-tree%22%3A%220.0.3%22%2C%22%40youwol%2Fflux-pack-shared-interfaces%22%3A%220.0.9%22%2C%22codemirror%22%3A%225.52.0%22%2C%22%40youwol%2Ffv-group%22%3A%220.0.3%22%2C%22%40youwol%2Ffv-button%22%3A%220.0.3%22%2C%22%40youwol%2Fflux-view%22%3A%220.0.6%22%2C%22%40youwol%2Fcdn%22%3A%220.0.0%22%2C%22%40youwol%2Fflux-lib-core%22%3A%221.8.0%22%2C%22rxjs%22%3A%226.5.5%22%2C%22reflect-metadata%22%3A%220.1.13%22%2C%22%40youwol%2Fflux-pack-utility-std%22%3A%221.2.2%22%7D%2C%22loadingGraph%22%3A%7B%22graphType%22%3A%22sequential-v1%22%2C%22lock%22%3A%5B%7B%22name%22%3A%22%40youwol%2Fflux-files%22%2C%22version%22%3A%220.0.0%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWZpbGVz%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-tree%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi10cmVl%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-pack-shared-interfaces%22%2C%22version%22%3A%220.0.9%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LXBhY2stc2hhcmVkLWludGVyZmFjZXM%3D%22%7D%2C%7B%22name%22%3A%22codemirror%22%2C%22version%22%3A%225.52.0%22%2C%22id%22%3A%22Y29kZW1pcnJvcg%3D%3D%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-group%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-button%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi1idXR0b24%3D%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-view%22%2C%22version%22%3A%220.0.6%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LXZpZXc%3D%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fcdn%22%2C%22version%22%3A%220.0.0%22%2C%22id%22%3A%22QHlvdXdvbC9jZG4%3D%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-lib-core%22%2C%22version%22%3A%221.8.0%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWxpYi1jb3Jl%22%7D%2C%7B%22name%22%3A%22rxjs%22%2C%22version%22%3A%226.5.5%22%2C%22id%22%3A%22cnhqcw%3D%3D%22%7D%2C%7B%22name%22%3A%22reflect-metadata%22%2C%22version%22%3A%220.1.13%22%2C%22id%22%3A%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-pack-utility-std%22%2C%22version%22%3A%221.2.2%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LXBhY2stdXRpbGl0eS1zdGQ%3D%22%7D%5D%2C%22definition%22%3A%5B%5B%5B%22Y29kZW1pcnJvcg%3D%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fcodemirror%2F5.52.0%2Fcodemirror.min.js%22%5D%2C%5B%22QHlvdXdvbC9jZG4%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Fcdn%2F0.0.0%2Fdist%2F%40youwol%2Fcdn.js%22%5D%2C%5B%22cnhqcw%3D%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Frxjs%2F6.5.5%2Frxjs.umd.min.js%22%5D%2C%5B%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Freflect-metadata%2F0.1.13%2Freflect-metadata.min.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mbHV4LXBhY2stc2hhcmVkLWludGVyZmFjZXM%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Fflux-pack-shared-interfaces%2F0.0.9%2Fdist%2Fbundles%2Fflux-pack-shared-interfaces.umd.min.js%22%5D%2C%5B%22QHlvdXdvbC9mbHV4LXZpZXc%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Fflux-view%2F0.0.6%2Fdist%2F%40youwol%2Fflux-view.js%22%5D%2C%5B%22QHlvdXdvbC9mbHV4LWxpYi1jb3Jl%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Fflux-lib-core%2F1.8.0%2Fdist%2Fbundles%2Fflux-lib-core.umd.min.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mdi10cmVl%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Ffv-tree%2F0.0.3%2Fdist%2F%40youwol%2Ffv-tree.js%22%5D%2C%5B%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Ffv-group%2F0.0.3%2Fdist%2F%40youwol%2Ffv-group.js%22%5D%2C%5B%22QHlvdXdvbC9mdi1idXR0b24%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Ffv-button%2F0.0.3%2Fdist%2F%40youwol%2Ffv-button.js%22%5D%2C%5B%22QHlvdXdvbC9mbHV4LXBhY2stdXRpbGl0eS1zdGQ%3D%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Fflux-pack-utility-std%2F1.2.2%2Fdist%2Fbundles%2Fflux-pack-utility-std.umd.min.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mbHV4LWZpbGVz%22%2C%22%2Fapi%2Fcdn-backend%2Flibraries%2Fyouwol%2Fflux-files%2F0.0.0%2Fdist%2F%40youwol%2Fflux-files.js%22%5D%5D%5D%7D%7D%2C%22workflow%22%3A%7B%22modules%22%3A%5B%7B%22configuration%22%3A%7B%22title%22%3A%22Local%20Drive%22%2C%22description%22%3A%22A%20module%20to%20connect%20to%20a%20local%20folder%20of%20the%20computer%20for%20fetching%2Fbrowsing%20files.%22%2C%22data%22%3A%7B%22driveId%22%3A%22local-drive%22%2C%22driveName%22%3A%22local-drive%22%7D%7D%2C%22moduleId%22%3A%22LocalDrive_635f8efb-261c-4828-b8b4-6a5fa80cf26c%22%2C%22factoryId%22%3A%7B%22module%22%3A%22LocalDrive%22%2C%22pack%22%3A%22%40youwol%2F%40youwol%2Fflux-files%22%7D%7D%2C%7B%22configuration%22%3A%7B%22title%22%3A%22Explorer%22%2C%22description%22%3A%22This%20module%20allows%20to%20explore%20files%20and%20data%20in%20your%20workspace%22%2C%22data%22%3A%7B%22selectionEmit%22%3A%22single%20file%20only%22%7D%7D%2C%22moduleId%22%3A%22Explorer_0556a4ea-009d-4d8e-8b38-a0abaf87777f%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Explorer%22%2C%22pack%22%3A%22%40youwol%2F%40youwol%2Fflux-files%22%7D%7D%2C%7B%22configuration%22%3A%7B%22title%22%3A%22Editor%22%2C%22description%22%3A%22Editor%22%2C%22data%22%3A%7B%22mode%22%3A%22javascript%22%2C%22theme%22%3A%22eclipse%22%2C%22lineNumbers%22%3Atrue%7D%7D%2C%22moduleId%22%3A%22Editor_a54e7226-9319-4d2c-8a28-c43ad97d88d2%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Editor%22%2C%22pack%22%3A%22%40youwol%2F%40youwol%2Fflux-files%22%7D%7D%2C%7B%22configuration%22%3A%7B%22title%22%3A%22Console%22%2C%22description%22%3A%22To%20log%20in%20the%20debug%20console%22%2C%22data%22%3A%7B%22prefix%22%3A%22Console%20Module%22%7D%7D%2C%22moduleId%22%3A%22Console_0b72323c-c8d4-46b4-acf7-4fac7bd2af3d%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Console%22%2C%22pack%22%3A%22%40youwol%2Fflux-pack-utility-std%22%7D%7D%5D%2C%22connections%22%3A%5B%7B%22start%22%3A%7B%22slotId%22%3A%22drive%22%2C%22moduleId%22%3A%22LocalDrive_635f8efb-261c-4828-b8b4-6a5fa80cf26c%22%7D%2C%22end%22%3A%7B%22slotId%22%3A%22drive%22%2C%22moduleId%22%3A%22Explorer_0556a4ea-009d-4d8e-8b38-a0abaf87777f%22%7D%2C%22adaptor%22%3A%7B%22configuration%22%3A%7B%22title%22%3A%22%22%2C%22description%22%3A%22%22%2C%22data%22%3A%7B%22code%22%3A%22%5Cnreturn%20(%7Bdata%2Cconfiguration%2Ccontext%7D)%20%3D%3E%20(%7B%5Cn%20%20%20%20data%3A%20%5Bdata%5D%2C%5Cn%20%20%20%20context%3A%7B%7D%2C%5Cn%20%20%20%20configuration%3A%20configuration%5Cn%7D)%22%7D%7D%2C%22adaptorId%22%3A%22e0c20b1d-f758-457d-af47-96be6b1c5359%22%7D%7D%2C%7B%22start%22%3A%7B%22slotId%22%3A%22selection%22%2C%22moduleId%22%3A%22Explorer_0556a4ea-009d-4d8e-8b38-a0abaf87777f%22%7D%2C%22end%22%3A%7B%22slotId%22%3A%22file%22%2C%22moduleId%22%3A%22Editor_a54e7226-9319-4d2c-8a28-c43ad97d88d2%22%7D%2C%22adaptor%22%3Anull%7D%2C%7B%22start%22%3A%7B%22slotId%22%3A%22content%22%2C%22moduleId%22%3A%22Editor_a54e7226-9319-4d2c-8a28-c43ad97d88d2%22%7D%2C%22end%22%3A%7B%22slotId%22%3A%22message%22%2C%22moduleId%22%3A%22Console_0b72323c-c8d4-46b4-acf7-4fac7bd2af3d%22%7D%2C%22adaptor%22%3A%7B%22configuration%22%3A%7B%22title%22%3A%22%22%2C%22description%22%3A%22%22%2C%22data%22%3A%7B%22code%22%3A%22%5Cnreturn%20(%7Bdata%2Cconfiguration%2Ccontext%7D)%20%3D%3E%20(%7B%5Cn%20%20%20%20data%3A%20data.isModified()%2C%5Cn%20%20%20%20context%3A%7B%7D%2C%5Cn%20%20%20%20configuration%3A%20configuration%5Cn%7D)%22%7D%7D%2C%22adaptorId%22%3A%22c3500c4f-dc89-497f-a411-3d346a37a374%22%7D%7D%5D%2C%22plugins%22%3A%5B%5D%2C%22rootLayerTree%22%3A%7B%22layerId%22%3A%22rootLayer%22%2C%22moduleIds%22%3A%5B%22LocalDrive_635f8efb-261c-4828-b8b4-6a5fa80cf26c%22%2C%22Explorer_0556a4ea-009d-4d8e-8b38-a0abaf87777f%22%2C%22Editor_a54e7226-9319-4d2c-8a28-c43ad97d88d2%22%2C%22Console_0b72323c-c8d4-46b4-acf7-4fac7bd2af3d%22%5D%2C%22title%22%3A%22rootLayer%22%2C%22children%22%3A%5B%5D%7D%7D%2C%22builderRendering%22%3A%7B%22modulesView%22%3A%5B%7B%22moduleId%22%3A%22LocalDrive_635f8efb-261c-4828-b8b4-6a5fa80cf26c%22%2C%22xWorld%22%3A-377.6476203070748%2C%22yWorld%22%3A407.2488064236111%7D%2C%7B%22moduleId%22%3A%22Explorer_0556a4ea-009d-4d8e-8b38-a0abaf87777f%22%2C%22xWorld%22%3A-47.50081380208334%2C%22yWorld%22%3A404.6866692437069%7D%2C%7B%22moduleId%22%3A%22Editor_a54e7226-9319-4d2c-8a28-c43ad97d88d2%22%2C%22xWorld%22%3A266.42774793836816%2C%22yWorld%22%3A401.220245361328%7D%2C%7B%22moduleId%22%3A%22Console_0b72323c-c8d4-46b4-acf7-4fac7bd2af3d%22%2C%22xWorld%22%3A622.5599500868054%2C%22yWorld%22%3A395.2341885036892%7D%5D%2C%22connectionsView%22%3A%5B%5D%2C%22descriptionsBoxes%22%3A%5B%5D%7D%2C%22runnerRendering%22%3A%7B%22layout%22%3A%22%3Cdiv%20id%3D%5C%22imer%5C%22%3E%3Cdiv%20id%3D%5C%22iyxp%5C%22%3E%3Cdiv%20id%3D%5C%22Explorer_0556a4ea-009d-4d8e-8b38-a0abaf87777f%5C%22%20class%3D%5C%22flux-element%5C%22%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%3Cdiv%20id%3D%5C%22i4wy%5C%22%3E%3Cdiv%20id%3D%5C%22Editor_a54e7226-9319-4d2c-8a28-c43ad97d88d2%5C%22%20class%3D%5C%22flux-element%5C%22%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%22%2C%22style%22%3A%22*%20%7B%20box-sizing%3A%20border-box%3B%20%7D%20body%20%7Bmargin%3A%200%3B%7D%23imer%7Bdisplay%3Aflex%3Bwidth%3A100%25%3Bheight%3A100%25%3Bpadding%3A5px%3B%7D%23iyxp%7Bmin-width%3A50px%3Bwidth%3A100%25%3B%7D%23i4wy%7Bmin-width%3A50px%3Bwidth%3A100%25%3B%7D%23Editor_a54e7226-9319-4d2c-8a28-c43ad97d88d2%7Bheight%3A100%25%3Bwidth%3A100%25%3B%7D%22%7D%7D>

