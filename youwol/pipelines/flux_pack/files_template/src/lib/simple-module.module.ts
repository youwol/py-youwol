import { Context, expectAnyOf, expectAttribute, expect as expect_, expectCount,
    BuilderView, Flux, Property, RenderView, Schema, ModuleFlux, Pipe
} from '@youwol/flux-core'
import { attr$, render } from "@youwol/flux-view"

import{pack} from './main'

/**
  ## Presentation

SimpleModule is an example included in the pipeline *flux-pack* of [YouWol](https://www.youwol.com/).
Its purpose is to provide an example of simple module in *Flux* that can be duplicated or updated.

The [[Module | module]] combines two numbers from an incoming message either using *addition* or *multiplication*
(see implementation [[Module.do | here]]). It features:
  -    one input, expected to get two numbers (or numbers compatible as defined by [[permissiveNumber]]).
  Input are defined using the method
  [addInput](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/classes/core_concepts.moduleflux.html#addinput)
  -    a [[renderHtmlElement | rendering view]], to display the results of the operation each time one is computed, or a default invite
  if no result have been computed yet
  -    an [[Module.result$ | output stream]], emitting the results for further use in your application.
  Output are added using [addOutput](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/classes/core_concepts.moduleflux.html#addOutput)
  -    a [[PersistentData | persistent data]], to save the operation's type within your application

 ## Resources

 Various resources:
 -    [flux-core documentation](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/core_concepts.html):
 the place to go to learn more about designing modules for flux
 -    [YouWol website](https://www.youwol.com/): the YouWol project presentation
 */
export namespace SimpleModule{

    let svgIcon = `<g transform="translate(0 -1)"><g><g>
    <path d="M477.931,436.328h-26.089l-70.651-108.646l12.978-2.433c2.624-0.492,4.867-2.183,6.063-4.571l34.113-68.227l0.002-0.005     l0.018-0.035c0.454-0.922,0.738-1.919,0.837-2.942l0.03-0.104c0.022-0.239-0.077-0.45-0.075-0.685     c0.044-0.682,0.005-1.367-0.117-2.039l-21.649-92.102c40.156-1.935,72.015-34.53,73.032-74.72     c1.017-40.19-29.152-74.354-69.16-78.317c-40.007-3.963-76.293,23.618-83.181,63.227l-74.2-37.101     c-0.183-0.092-0.383-0.077-0.569-0.154c-0.284-0.133-0.576-0.25-0.873-0.35c-0.253-0.074-0.499-0.116-0.758-0.167     c-0.26-0.051-0.507-0.106-0.769-0.132c-0.282-0.018-0.565-0.022-0.847-0.011c-0.285-0.011-0.57-0.006-0.854,0.014     c-0.257,0.026-0.498,0.078-0.754,0.128c-0.266,0.051-0.517,0.094-0.777,0.17c-0.294,0.1-0.582,0.217-0.863,0.35     c-0.186,0.077-0.386,0.063-0.569,0.154L145.131,81.186V68.183c16.643-4.297,27.494-20.299,25.328-37.35S153.786,1,136.597,1     s-31.695,12.781-33.861,29.832c-2.166,17.051,8.685,33.053,25.328,37.35V89.72l-12.35,6.175     c-2.265,1.133-3.911,3.214-4.492,5.679L77.089,246.641c-0.119,0.667-0.158,1.346-0.115,2.023     c0.002,0.241-0.099,0.458-0.077,0.702l0.031,0.103c0.099,1.023,0.382,2.02,0.835,2.943l34.133,68.267     c1.195,2.388,3.438,4.079,6.063,4.571l12.98,2.434l-70.65,108.645H34.197c-9.422,0.009-17.057,7.645-17.067,17.067v25.6     c0,4.713,3.82,8.533,8.533,8.533h102.4c4.713,0,8.533-3.82,8.533-8.533v-25.6c-0.009-9.422-7.645-17.057-17.067-17.067h-4.757     l30.148-46.386l85.542,22.821v49.165h-17.067c-9.422,0.009-17.057,7.645-17.067,17.067v25.6c0,4.713,3.82,8.533,8.533,8.533     h102.4c4.713,0,8.533-3.82,8.533-8.533v-25.6c-0.009-9.422-7.645-17.057-17.067-17.067h-17.067v-49.165l85.542-22.821     l30.148,46.386h-4.757c-9.422,0.009-17.057,7.645-17.067,17.067v25.6c0,4.713,3.82,8.533,8.533,8.533h102.4     c2.263,0.001,4.434-0.898,6.035-2.499s2.499-3.771,2.499-6.035v-25.6C494.986,443.973,487.352,436.339,477.931,436.328z      M386.86,309.253l-21.263,3.987l-0.044,0.009l-55.688,10.442l28.651-74.545l74.987,6.817L386.86,309.253z M409.664,18.195     c32.99,0,59.733,26.744,59.733,59.733s-26.743,59.733-59.733,59.733c-32.99,0-59.733-26.744-59.733-59.733     C349.969,44.954,376.69,18.233,409.664,18.195z M333.138,83.34c2.497,34.816,28.141,63.577,62.443,70.035l20.132,85.652     l-75.812-6.862L315.61,118.807c-0.102-0.306-0.22-0.605-0.355-0.898c-0.116-0.368-0.259-0.728-0.425-1.077     c-0.101-0.204-0.132-0.434-0.249-0.63L278.459,56L333.138,83.34z M322.309,231.53l-132.497,0.029l21.949-102.431h88.605     L322.309,231.53z M256.064,51.847l36.129,60.214h-72.258L256.064,51.847z M119.531,35.261c0-9.426,7.641-17.067,17.067-17.067     s17.067,7.641,17.067,17.067s-7.641,17.067-17.067,17.067C127.176,52.318,119.54,44.683,119.531,35.261z M126.922,109.374     L233.669,56l-36.122,60.203c-0.117,0.195-0.148,0.426-0.249,0.63c-0.167,0.348-0.309,0.708-0.425,1.077     c-0.135,0.293-0.253,0.592-0.355,0.898L172.235,232.13l-75.821,6.893L126.922,109.374z M125.268,309.253l-26.649-53.296     l74.98-6.846l28.663,74.578l-55.683-10.441l-0.048-0.009L125.268,309.253z M119.531,453.395v17.067H34.197v-17.067H119.531z      M134.376,374.853l-0.006,0.01l-39.949,61.466H80.645l68.439-105.243l12.247,2.296L134.376,374.853z M154.707,374.887     l24.765-38.104l50.992,9.561v48.753L154.707,374.887z M298.731,478.995v17.067h-85.333v-17.067H298.731z M247.531,461.928     V349.545l6.954,1.304c0.512,0.094,1.032,0.142,1.553,0.143l0.018,0.003l0.009-0.001l0.009,0.001l0.018-0.003     c0.521,0,1.041-0.048,1.553-0.143l6.954-1.304v112.383H247.531z M256.064,333.777l-34.094-6.393l-30.286-78.793l128.771-0.028     l-30.297,78.821L256.064,333.777z M281.664,395.098v-48.753l50.992-9.561l24.765,38.104L281.664,395.098z M350.798,333.381     l12.244-2.295l68.445,105.242h-13.772L350.798,333.381z M477.931,470.461h-85.333v-17.067h85.333V470.461z"/>
    <path d="M409.664,112.061c18.851,0,34.133-15.282,34.133-34.133s-15.282-34.133-34.133-34.133     c-18.851,0-34.133,15.282-34.133,34.133C375.551,96.771,390.821,112.041,409.664,112.061z M409.664,60.861     c9.426,0,17.067,7.641,17.067,17.067s-7.641,17.067-17.067,17.067c-9.426,0-17.067-7.641-17.067-17.067     C392.608,68.507,400.243,60.872,409.664,60.861z"/>
    </g></g></g>`

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
     * implementation:
     *
     * ```typescript
     * let operationsFactory = {
     *      [Operations.ADDITION] : (d: [number, number]) => d[0] + d[1],
     *      [Operations.MULTIPLICATION] : (d: [number, number]) => d[0] * d[1],
     * }
     * ```
     */
    export let operationsFactory = {
        [Operations.ADDITION] : (d: [number, number]) => d[0] + d[1],
        [Operations.MULTIPLICATION] : (d: [number, number]) => d[0] * d[1],
    }

    /**
     * ## Persistent Data  🔧
     *
     * The persistent data (or configuration) defines the property *operation type*, see [[Operations]].
     *
     * To learn more:
     * [@Schema decorator](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/lib_models_decorators.html#schema),
     * [configuration](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/classes/core_concepts.moduleconfiguration.html)
     *
     */
    @Schema({
        pack
    })
    export class PersistentData {

        @Property({
            description: "operation type",
            enum: Object.values(Operations)
        })
        operationType : Operations

        constructor({operationType} :{operationType?:Operations}= {}) {

            /*
             * operationType is set to addition by default
             */
            this.operationType = (operationType != undefined)
                ? operationType
                : Operations.ADDITION
        }
    }

    /**
     * This is a building block of the contract associated to the module's input:
     * an expectation fulfilled only if the incoming data
     * is a number ```(inputData) => typeof (inputData) == 'number' ```
     * See [[permissiveNumber]]
     *
     * To learn more about contract:
     * [contract documentation](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/contract.html)
     */
    export let straightNumber = expect_<number>({
        description: `a straight number`,
        when: (inputData) => typeof (inputData) == 'number'
    })

    /**
     * This is a building block of the contract associated to the module's input.
     *
     * A *permissiveNumber* is either:
     * -    a straight *number*
     * -    an object of type *{value: number}*
     *
     * See [[straightNumber]]
     *
     * To learn more about contract:
     * [contract documentation](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/contract.html)
     */
    export let permissiveNumber = expectAnyOf<number>({
        description: `an implicit number`,
        when: [
            straightNumber,
            expectAttribute({ name: 'value', when: straightNumber })
        ]
    })

    /** ## Module
     *
     * The module's definition:
     * -    the logic is defined in [[do]]
     * -    the view in the *builder-panel* is defined using the decorator
     * [@BuilderView](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/lib_models_decorators.html#builderview)
     * -    the view in the *rendering-panel* is defined using the decorator
     * [@RenderView](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/lib_models_decorators.html#renderview)
     *
     * Module needs to derive from [ModuleFlux](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/classes/core_concepts.moduleflux.html)
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
    @BuilderView({
        namespace: SimpleModule,
        icon: svgIcon
    })
    @RenderView({
        namespace: SimpleModule,
        render: (mdle: Module) => renderHtmlElement(mdle)
    })
    export class Module extends ModuleFlux {

        /**
         * This is the output, you can use it to emit messages using *this.result$.next(...)*.
         *
         */
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
        * Processing function triggered when a message is received
        */
        do( data: [number, number], configuration: PersistentData, context: Context ) {

            let result = operationsFactory[configuration.operationType](data)
            context.info('Computation done', {result})
            this.result$.next({data:result,context})
        }
    }

    /**
     * This function defines how to render the module in the *rendering-panel*.
     *
     * To learn more:
     * -    [@RenderView decorator](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/lib_models_decorators.html#renderview)
     * -    [flux-view](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LXZpZXc=/latest/dist/docs/index.html)
     *
     * Note: You can use any of your favorite framework to render the view, *flux-view* is what we use @ YouWol.
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