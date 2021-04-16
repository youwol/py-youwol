
import { pack } from './main';
import {Property, Flux, BuilderView,ModuleFlow,Pipe,Schema} from '@youwol/flux-lib-core'


/**
    ## abstract

    This is the first example of this 'tutorial'.

    Here we'll cover some basics concepts that will get you started with the definition of
    a 'computer' like module: a module that basically does some computations. More elaborated example
    (module with view, plugins, etc) will come in following examples.


    ## Everything start with a namespace

    Defining a module starts with the definition of a namespace that will gather all related data structures.
    In this particular case, we called the namespace 'Example0', it also refers to the name of the module.

    For a simple *'computer'* like module, the namespace includes:
    -    the definition of an icon, see [[svgIcon]]
    -    the definition of a set of a [[Example0.PersistentData | configuration]]
    -    the definition of the [[Example0.Module | module's logic ]]

*/
export namespace Example0 {

    /**
    This svg image is used as icon of the module (it is referenced in the 'Flux' decorator).
    You should not worry about the size of the image: it will be scaled appropriately automatically.

    You can get svg images from various sources, e.g. [flaticon](https://www.flaticon.com).
    */
    //Icons made by <a href="https://www.flaticon.com/authors/smashicons" title="Smashicons">Smashicons</a> from <a href="https://www.flaticon.com/" title="Flaticon"> www.flaticon.com</a>
    export let svgIcon = `
<g transform="translate(0 -1)">
	<g>
		<g>
			<path d="M477.931,436.328h-26.089l-70.651-108.646l12.978-2.433c2.624-0.492,4.867-2.183,6.063-4.571l34.113-68.227l0.002-0.005     l0.018-0.035c0.454-0.922,0.738-1.919,0.837-2.942l0.03-0.104c0.022-0.239-0.077-0.45-0.075-0.685     c0.044-0.682,0.005-1.367-0.117-2.039l-21.649-92.102c40.156-1.935,72.015-34.53,73.032-74.72     c1.017-40.19-29.152-74.354-69.16-78.317c-40.007-3.963-76.293,23.618-83.181,63.227l-74.2-37.101     c-0.183-0.092-0.383-0.077-0.569-0.154c-0.284-0.133-0.576-0.25-0.873-0.35c-0.253-0.074-0.499-0.116-0.758-0.167     c-0.26-0.051-0.507-0.106-0.769-0.132c-0.282-0.018-0.565-0.022-0.847-0.011c-0.285-0.011-0.57-0.006-0.854,0.014     c-0.257,0.026-0.498,0.078-0.754,0.128c-0.266,0.051-0.517,0.094-0.777,0.17c-0.294,0.1-0.582,0.217-0.863,0.35     c-0.186,0.077-0.386,0.063-0.569,0.154L145.131,81.186V68.183c16.643-4.297,27.494-20.299,25.328-37.35S153.786,1,136.597,1     s-31.695,12.781-33.861,29.832c-2.166,17.051,8.685,33.053,25.328,37.35V89.72l-12.35,6.175     c-2.265,1.133-3.911,3.214-4.492,5.679L77.089,246.641c-0.119,0.667-0.158,1.346-0.115,2.023     c0.002,0.241-0.099,0.458-0.077,0.702l0.031,0.103c0.099,1.023,0.382,2.02,0.835,2.943l34.133,68.267     c1.195,2.388,3.438,4.079,6.063,4.571l12.98,2.434l-70.65,108.645H34.197c-9.422,0.009-17.057,7.645-17.067,17.067v25.6     c0,4.713,3.82,8.533,8.533,8.533h102.4c4.713,0,8.533-3.82,8.533-8.533v-25.6c-0.009-9.422-7.645-17.057-17.067-17.067h-4.757     l30.148-46.386l85.542,22.821v49.165h-17.067c-9.422,0.009-17.057,7.645-17.067,17.067v25.6c0,4.713,3.82,8.533,8.533,8.533     h102.4c4.713,0,8.533-3.82,8.533-8.533v-25.6c-0.009-9.422-7.645-17.057-17.067-17.067h-17.067v-49.165l85.542-22.821     l30.148,46.386h-4.757c-9.422,0.009-17.057,7.645-17.067,17.067v25.6c0,4.713,3.82,8.533,8.533,8.533h102.4     c2.263,0.001,4.434-0.898,6.035-2.499s2.499-3.771,2.499-6.035v-25.6C494.986,443.973,487.352,436.339,477.931,436.328z      M386.86,309.253l-21.263,3.987l-0.044,0.009l-55.688,10.442l28.651-74.545l74.987,6.817L386.86,309.253z M409.664,18.195     c32.99,0,59.733,26.744,59.733,59.733s-26.743,59.733-59.733,59.733c-32.99,0-59.733-26.744-59.733-59.733     C349.969,44.954,376.69,18.233,409.664,18.195z M333.138,83.34c2.497,34.816,28.141,63.577,62.443,70.035l20.132,85.652     l-75.812-6.862L315.61,118.807c-0.102-0.306-0.22-0.605-0.355-0.898c-0.116-0.368-0.259-0.728-0.425-1.077     c-0.101-0.204-0.132-0.434-0.249-0.63L278.459,56L333.138,83.34z M322.309,231.53l-132.497,0.029l21.949-102.431h88.605     L322.309,231.53z M256.064,51.847l36.129,60.214h-72.258L256.064,51.847z M119.531,35.261c0-9.426,7.641-17.067,17.067-17.067     s17.067,7.641,17.067,17.067s-7.641,17.067-17.067,17.067C127.176,52.318,119.54,44.683,119.531,35.261z M126.922,109.374     L233.669,56l-36.122,60.203c-0.117,0.195-0.148,0.426-0.249,0.63c-0.167,0.348-0.309,0.708-0.425,1.077     c-0.135,0.293-0.253,0.592-0.355,0.898L172.235,232.13l-75.821,6.893L126.922,109.374z M125.268,309.253l-26.649-53.296     l74.98-6.846l28.663,74.578l-55.683-10.441l-0.048-0.009L125.268,309.253z M119.531,453.395v17.067H34.197v-17.067H119.531z      M134.376,374.853l-0.006,0.01l-39.949,61.466H80.645l68.439-105.243l12.247,2.296L134.376,374.853z M154.707,374.887     l24.765-38.104l50.992,9.561v48.753L154.707,374.887z M298.731,478.995v17.067h-85.333v-17.067H298.731z M247.531,461.928     V349.545l6.954,1.304c0.512,0.094,1.032,0.142,1.553,0.143l0.018,0.003l0.009-0.001l0.009,0.001l0.018-0.003     c0.521,0,1.041-0.048,1.553-0.143l6.954-1.304v112.383H247.531z M256.064,333.777l-34.094-6.393l-30.286-78.793l128.771-0.028     l-30.297,78.821L256.064,333.777z M281.664,395.098v-48.753l50.992-9.561l24.765,38.104L281.664,395.098z M350.798,333.381     l12.244-2.295l68.445,105.242h-13.772L350.798,333.381z M477.931,470.461h-85.333v-17.067h85.333V470.461z"/>
			<path d="M409.664,112.061c18.851,0,34.133-15.282,34.133-34.133s-15.282-34.133-34.133-34.133     c-18.851,0-34.133,15.282-34.133,34.133C375.551,96.771,390.821,112.041,409.664,112.061z M409.664,60.861     c9.426,0,17.067,7.641,17.067,17.067s-7.641,17.067-17.067,17.067c-9.426,0-17.067-7.641-17.067-17.067     C392.608,68.507,400.243,60.872,409.664,60.861z"/>
		</g>
	</g>
</g>`


    /**
    ## Abstract

    The persistent data represents the configuration of the module. As its name suggest, the attributes
    defined here can be updated by the user and will be persisted when saving a 'Flux' project.

    ## To be continued

    Need to talk about:
    -    default values & types authorized
    -    automatic generation of the settings UI
    -    dynamically overriding values
    */
    @Schema({
        pack: pack,
        description: "Persistent data for the module 'example'",
        namespace: Example0,
    })
    export class PersistentData {

        @Property({ description: "value of the property", type: "string" })
        readonly value : string

        constructor( {value} : {value?: string} = {}) {
            this.value = value ? value : "some config value"
        }
    }

    /**
    ## Abstract

    The Module class defines the logic of the module.

    ## To be continued

    Need to talk about:
    -    inputs, outputs
    -    input data: {data, configuration, context}
    -    input's contract
    -    caching
    */
    @Flux({
        pack:           pack,
        namespace:      Example0,
        id:             "Example0",
        displayName:    "Example0",
        description:    "The first example of our tutorial"
    })
    @BuilderView({
        namespace:      Example0,
        icon:           svgIcon
    })
    export class Module extends ModuleFlow {
        
        output$ : Pipe<Object>

        constructor(params){ 
            super(params)                   
            this.addInput("input", Object, this.execute )
            this.output$ = this.addOutput("output", Object) 
            let config = this.getConfiguration<PersistentData>()
            this.output$.next({data:config.value})
        }

        execute( data: any, configuration:PersistentData, context: any){

            console.log("Module executed", {data, configuration, context})
            this.output$.next({data:"some new value", context})
        }
    }

}
