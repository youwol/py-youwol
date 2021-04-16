import { Context, expectAnyOf, expectAttribute, expect as expect_, expectCount,
    BuilderView, Flux, Property, RenderView, Schema, ModuleFlux, Pipe
} from '@youwol/flux-core'
import { attr$, render } from "@youwol/flux-view"

import{pack} from './main'

/**
  ## Module's namespace  🏭

 All the data related to one module are encapsulated in a namespace.
 In particular, it includes the definition of:
 -    the persistentData: data of the module the user will be able to save wit their application
 -    the core logic: what is happening when an input of the module recieved some data
 -    the rendering view: how the user will see and interact with your module in the application;
 not all modules have a rendering view associated (e.g. a pure computational module won't).

 The namespace can also includes the definition of a custom view for the rendering in the **builder
 panel**, featuring dynamic interactions with the module's configuration. This is for instance the case
 of the *Combine* type of modules for which you can control the number of inputs from the builder view.
 However, most of the time, the default representation is enough.

 > 🧐 On top of the classes/structures explicitly written in it, the decorators are generating other
 > required data in the namespace (that you don't need to care about). At the end of the day
 > the namespace is actually the [Factory](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_models_base.html#factory) for the module.
 > Detailed documentation about Flux modules can be found in the
 [flux-core documentation](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_models_base.moduleflux.html).

  ## Current example

  The current example define a module combining two numbers either using *addition* or *multiplication*. It features:
  -    one input expected to get two numbers (or numbers compatible as it'll be defined)
  -    a rendering view to display the results of the operation each time one is computed, or a default invite
  if no result have been computed yet
  -    an output streaming the results for further use in your application
  -    a persistent data side to save the operation type within your application

  Should you want to include other type of operations, you can have a look to [[Operations]] and [[operationsFactory]].
  ### [[PersistentData  | Persistent data]]

  ### [[Module | Core logic]]

  ### [[renderHtmlElement | Rendering view ]]
 */
export namespace SimpleModule{

    /**
     * These are the two operations implemented: you can add additional items here and
     * define their implementation in the [[operationsFactory]] variable.
     *
     */
    export enum Operations{
        ADDITION= 'addition',
        MULTIPLICATION= 'multiplication'
    }
    /**
     * The operations factory links the enum [[Operations]] to their actual
     * implementation.
     */
    export let operationsFactory = {
        [Operations.ADDITION] : (d: [number, number]) => d[0] + d[1],
        [Operations.MULTIPLICATION] : (d: [number, number]) => d[0] * d[1],
    }

    /**
     * ## Persistent Data  🔧
     *
     * The persistent data of the module defines the configuration:
     * it is some data required by the processing function(s) of your module
     * that can be changed and saved from the UI.
     *
     * The attributes of the persistent data are automatically exposed
     * in the **builder side** of the application: they are meant to be defined
     * by the developer of the application at construction. Those data won't be
     * exposed in the **rendering side**: the user running the application won't be
     * able to access it by default.
     *
     * > Even though the configuration is hidden to the final user, you still
     * > may want to expose it (or part of it) to the user. This is definitely possible:
     * > you can add some widgets (e.g. sliders, drop down menu, etc) to overide the values
     * > saved using adaptors. You can also use the Flux plugin 'AutoForm' that exposes
     * > in the rendering side an auto-generated widget enabling to play
     * > with the attributes of your persistent data.
     *
     * ### Decorators 🎀
     *
     * To provide persistent data to your module:
     * -    defines a class 'PersistentData' in your namespace
     * -    decorate this class with the typescript decorator [@Schema](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_decorators.html#schema)
     * -    define the properties you need using the typescript decorator [@Property](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_decorators.html#property)
     * -    you can use complex types as properties (e.g. Vector, Matrix) as long as these types are classes decorated with *@Schema*
     * -    you can derive your PesistentData class from other classes, their exposed properties will be part of your configuration
     * (providing that these classes also use the *@Schema* and *@Property* decorators).
     *
     * You can look at [[constructor]] for hints about properties initialization.
     */
    @Schema({
        pack
    })
    export class PersistentData {

        /* The decorator 'Property' is used to declare an attribute that can be:
        * -    updated by the user in the builder view of a flux app
        * -    overided at run time (see in the tests below)
        *
        * Basic types can be used, as well as custom classes (as long as they are decorated with 'Schema').
        */
        @Property({
            description: "operation type",
            enum: Object.values(Operations)
        })
        operationType : Operations

        /** The next snippet present the general case of a PesistentData that
         * encaspulates others @Schema data types (it is not related to the actual example).
         *
         *
         * ``` typescript
         *  // To provide an example of PersistentData inheriting from an existing class
         *  @Schema({pack}) export class SomeBaseModel{
         *      // define some @Property
         *  }
         *
         *  // To provide an example of PersistentData composing from an existing class
         *  @Schema({pack}) export class Vector3D{
         *
         *      @Property({description: 'x coordinates'}) x: number
         *      @Property({description: 'y coordinates'}) y: number
         *      @Property({description: 'z coordinates'}) z: number
         *
         *      constructor({x, y, z} :{x?:number, y?: number, z?: number}= {
         *          this.x = x != undefined ? x : 0         *
         *          this.y = y != undefined ? y : 0
         *          this.z = z != undefined ? z : 0
         *      })
         *  }
         *
         *  @Schema({pack})
         *  // We want to inherit all the properties defined in the class SomeBaseModel
         *  export class PersistentData extends SomeBaseModel {
         *
         *      @Property({
         *          description: 'a simple type',
         *          type: 'integer' // simple types may have some additional description available
         *      })
         *      value0 : number
         *
         *      @Property({
         *          description: 'a nested type'
         *      })
         *      value1 : Vector3D
         *
         *      constructor({value0, value1, ...rest} :{value0?:number, value1?: Vector3D}= {}) {
         *          // this next line call the construction of SomeBaseConfiguration by forwarding the required parameters
         *          super(rest)
         *          // the default values of the properties are defined here
         *          this.value0 = value0 != undefined ? value0 : 0
         *          this.value1 = value1 != undefined ? value1 : new Vector3D({x:0,y:0,z:0})
         *      }
         * }
         * ```
         */
        constructor({operationType} :{operationType?:Operations}= {}) {

            /*
             * operationType is set to addition by default
             */
            this.operationType = (operationType != undefined)
                ? operationType
                : Operations.ADDITION
        }
    }

    /*
     * The next ~10 lines declares the contract of the input, from which we expect to retrieve two numbers.
     * One of the responsability of the developer is to try to be as flexible as possible in terms of
     * acceptable data. Here we define a contract that can accept either directly a number
     * or an object in the form *{value:number}*.
     */
    export let straightNumber = expect_<number>({
        description: `a straight number`,
        when: (inputData) => typeof (inputData) == 'number'
    })

    export let permissiveNumber = expectAnyOf<number>({
        description: `an implicit number `,
        when: [
            straightNumber,
            expectAttribute({ name: 'value', when: straightNumber })
        ]
    })

    /** ## The processing  🎬
     *
     * To declare the processing logic of the module, start by an empty shell:
     * -    declare a class Module that inherits from [ModuleFlux](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_models_base.moduleflux.html)
     * -    decorate your class with [@Flux](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_decorators.html#flux),
     * [@BuilderView](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_decorators.html#builderview) and eventually
     * [@RenderView](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/libraries/youwol/flux-core/latest/dist/docs/modules/lib_models_decorators.html#builderview)
     * (they define respectively: (i) some general info about your module, (ii) how to render the module in the **builder panel**, and
     * (iii) how to render the module in the **render panel** (optional, if a view is actually needed)).
     *
     * A simple example would look like this:
     *
     * ```typescript
     * @Flux({
     *   pack: pack,
     *   namespace: SimpleModule,
     *   id: "SimpleModule",
     *   displayName: "simple module",
     *   description: "A module that does addition or multiplication :/ ",
     *   resources: { 'technical doc': `...`, 'github': '...' }
     * })
     * // This declare a default BuilderView wit custom icon
     * @BuilderView({
     *   namespace: SimpleModule,
     *   icon: `<text> Hello </text>` // any svg element (or group of elements) can be used, this image will be used for the default display in the builder panel
     * })
     * @RenderView({
     *   namespace: SimpleModule,
     *   render: (mdle: Module) => new HTMLDivElement() // an empty div for now
     *})
     * export class Module extends ModuleFlux {
     *
     *   constructor( params ){
     *       super(params)
     *       // To be continued ...
     *   }
     * ```
     *
     * > It is a bit unfortunate that we have to repeat ```namespace: SimpleModule``` in all decorators (we did not find a way to access it automatically),
     * > hopefully this may be resolved in the future.
     *
     * From there it remains:
     * -    declaring the input(s) of the module
     * -    declaring the output(s) of the module
     * -    implementing the processing
     * -    defining the view
     *
     * ### Inputs
     *
     * ### Outputs
     *
     * ### Processing
     *
     * ### View
     *
     */
    @Flux({
        pack: pack,
        namespace: SimpleModule,
        id: "SimpleModule",
        displayName: "A simple module",
        description: "A module that does addition or multiplication :/ ",
        resources: {
            'technical doc': `${pack.urlCDN}/dist/docs/modules/lib_simple_module_module.simplemodule.html`
        }
    })
    /**
     * This decorator allows to define the view of the module in the builder panel.
     * An automatic view can be generated by providing a svg definition of an icon.
     * The BuilderView can also be defined by a custom function that can interact
     * with the module's configuration.
     */
    @BuilderView({
        namespace: SimpleModule,
        icon: `<g transform="translate(0 -1)"><g><g>
        <path d="M477.931,436.328h-26.089l-70.651-108.646l12.978-2.433c2.624-0.492,4.867-2.183,6.063-4.571l34.113-68.227l0.002-0.005     l0.018-0.035c0.454-0.922,0.738-1.919,0.837-2.942l0.03-0.104c0.022-0.239-0.077-0.45-0.075-0.685     c0.044-0.682,0.005-1.367-0.117-2.039l-21.649-92.102c40.156-1.935,72.015-34.53,73.032-74.72     c1.017-40.19-29.152-74.354-69.16-78.317c-40.007-3.963-76.293,23.618-83.181,63.227l-74.2-37.101     c-0.183-0.092-0.383-0.077-0.569-0.154c-0.284-0.133-0.576-0.25-0.873-0.35c-0.253-0.074-0.499-0.116-0.758-0.167     c-0.26-0.051-0.507-0.106-0.769-0.132c-0.282-0.018-0.565-0.022-0.847-0.011c-0.285-0.011-0.57-0.006-0.854,0.014     c-0.257,0.026-0.498,0.078-0.754,0.128c-0.266,0.051-0.517,0.094-0.777,0.17c-0.294,0.1-0.582,0.217-0.863,0.35     c-0.186,0.077-0.386,0.063-0.569,0.154L145.131,81.186V68.183c16.643-4.297,27.494-20.299,25.328-37.35S153.786,1,136.597,1     s-31.695,12.781-33.861,29.832c-2.166,17.051,8.685,33.053,25.328,37.35V89.72l-12.35,6.175     c-2.265,1.133-3.911,3.214-4.492,5.679L77.089,246.641c-0.119,0.667-0.158,1.346-0.115,2.023     c0.002,0.241-0.099,0.458-0.077,0.702l0.031,0.103c0.099,1.023,0.382,2.02,0.835,2.943l34.133,68.267     c1.195,2.388,3.438,4.079,6.063,4.571l12.98,2.434l-70.65,108.645H34.197c-9.422,0.009-17.057,7.645-17.067,17.067v25.6     c0,4.713,3.82,8.533,8.533,8.533h102.4c4.713,0,8.533-3.82,8.533-8.533v-25.6c-0.009-9.422-7.645-17.057-17.067-17.067h-4.757     l30.148-46.386l85.542,22.821v49.165h-17.067c-9.422,0.009-17.057,7.645-17.067,17.067v25.6c0,4.713,3.82,8.533,8.533,8.533     h102.4c4.713,0,8.533-3.82,8.533-8.533v-25.6c-0.009-9.422-7.645-17.057-17.067-17.067h-17.067v-49.165l85.542-22.821     l30.148,46.386h-4.757c-9.422,0.009-17.057,7.645-17.067,17.067v25.6c0,4.713,3.82,8.533,8.533,8.533h102.4     c2.263,0.001,4.434-0.898,6.035-2.499s2.499-3.771,2.499-6.035v-25.6C494.986,443.973,487.352,436.339,477.931,436.328z      M386.86,309.253l-21.263,3.987l-0.044,0.009l-55.688,10.442l28.651-74.545l74.987,6.817L386.86,309.253z M409.664,18.195     c32.99,0,59.733,26.744,59.733,59.733s-26.743,59.733-59.733,59.733c-32.99,0-59.733-26.744-59.733-59.733     C349.969,44.954,376.69,18.233,409.664,18.195z M333.138,83.34c2.497,34.816,28.141,63.577,62.443,70.035l20.132,85.652     l-75.812-6.862L315.61,118.807c-0.102-0.306-0.22-0.605-0.355-0.898c-0.116-0.368-0.259-0.728-0.425-1.077     c-0.101-0.204-0.132-0.434-0.249-0.63L278.459,56L333.138,83.34z M322.309,231.53l-132.497,0.029l21.949-102.431h88.605     L322.309,231.53z M256.064,51.847l36.129,60.214h-72.258L256.064,51.847z M119.531,35.261c0-9.426,7.641-17.067,17.067-17.067     s17.067,7.641,17.067,17.067s-7.641,17.067-17.067,17.067C127.176,52.318,119.54,44.683,119.531,35.261z M126.922,109.374     L233.669,56l-36.122,60.203c-0.117,0.195-0.148,0.426-0.249,0.63c-0.167,0.348-0.309,0.708-0.425,1.077     c-0.135,0.293-0.253,0.592-0.355,0.898L172.235,232.13l-75.821,6.893L126.922,109.374z M125.268,309.253l-26.649-53.296     l74.98-6.846l28.663,74.578l-55.683-10.441l-0.048-0.009L125.268,309.253z M119.531,453.395v17.067H34.197v-17.067H119.531z      M134.376,374.853l-0.006,0.01l-39.949,61.466H80.645l68.439-105.243l12.247,2.296L134.376,374.853z M154.707,374.887     l24.765-38.104l50.992,9.561v48.753L154.707,374.887z M298.731,478.995v17.067h-85.333v-17.067H298.731z M247.531,461.928     V349.545l6.954,1.304c0.512,0.094,1.032,0.142,1.553,0.143l0.018,0.003l0.009-0.001l0.009,0.001l0.018-0.003     c0.521,0,1.041-0.048,1.553-0.143l6.954-1.304v112.383H247.531z M256.064,333.777l-34.094-6.393l-30.286-78.793l128.771-0.028     l-30.297,78.821L256.064,333.777z M281.664,395.098v-48.753l50.992-9.561l24.765,38.104L281.664,395.098z M350.798,333.381     l12.244-2.295l68.445,105.242h-13.772L350.798,333.381z M477.931,470.461h-85.333v-17.067h85.333V470.461z"/>
        <path d="M409.664,112.061c18.851,0,34.133-15.282,34.133-34.133s-15.282-34.133-34.133-34.133     c-18.851,0-34.133,15.282-34.133,34.133C375.551,96.771,390.821,112.041,409.664,112.061z M409.664,60.861     c9.426,0,17.067,7.641,17.067,17.067s-7.641,17.067-17.067,17.067c-9.426,0-17.067-7.641-17.067-17.067     C392.608,68.507,400.243,60.872,409.664,60.861z"/>
        </g></g></g>`
    })
    /**
    * This decorator allows to define a view in the rendering panel.
    * In the case of a 'processing' module (no rendering view associated),
    * this part is not included.
    *  The view is defined by a function that return a HTMLDivElement,
    * there can be any interaction between the view and the module's logic
    * (altough not illustrated by this example).
    */
    @RenderView({
        namespace: SimpleModule,
        render: (mdle: Module) => renderHtmlElement(mdle)
    })
    export class Module extends ModuleFlux {

        result$ : Pipe<number>

        constructor( params ){
            super(params)

            this.addInput({
                id:'input',
                description: 'trigger an operation between 2 numbers',
                contract: expectCount<number>( {count:2, when:permissiveNumber}),
                onTriggered: ({data, configuration, context}) => this.do(data, configuration, context)
            })
            this.result$ = this.addOutput({id:'result'})
        }

        /**
        * Thanks to the contract defined in the input, the type of the data that is passed
        * in the above 'onTriggered' function is known (here [number, number]).
        *
        * Regarding the configuration, the instance passed is a merge between:
        * -   the default configuration as defined by the user
        * -   the eventual attributes of the configuration that have been overide at run time
        * (e.g. using an adaptor)
        *
        * The context is essentially used in the function to report info, warning, errors,
        * timings, graphs, etc; a nice report is then accessible to the user to better
        * understand what happened in the process.
        */
        do( data: [number, number], configuration: PersistentData, context: Context ) {

            let result = operationsFactory[configuration.operationType](data)
            context.info('Computation done', {result})
            this.result$.next({data:result,context})
        }
    }

    /**
     * This function defines how to render the module in the rendering panel.
     * Here we use a label to display the last result computed.
     *
     * Any framework, if need be, can be used here (as long as a HTMLElement is returned).
     * We find @YouWol our library https://github.com/youwol/flux-view particularly suited
     * to define view within flux applications.
     */
    export function renderHtmlElement(mdle: Module) : HTMLElement {

        return render({
            tag: 'label',
            class: 'fv-bg-background fv-text-primary p-2 border rounded fv-color-focus',

            /* 'attr$' bind an HTML's attributes (here innerText)
             * to a rxjs observable (here the module output mdle.result$).
             */
            innerText: attr$(
                mdle.result$,
                ({data}) => {
                    return `The last computed result is: ${data}`
                },
                {untilFirst: "No data have reach the module yet. You can connect it to a 'CombineLatest' combining two sliders."}
            )
        })
    }
}
