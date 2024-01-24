import { AnyVirtualDOM, ChildrenLike, VirtualDOM } from '@youwol/rx-vdom'
import { Routers } from '@youwol/local-youwol-client'

type HeadingLevel = 'h1' | 'h2' | 'h3' | 'h4'
type Doc =
    | Routers.System.DocClassResponse
    | Routers.System.DocFunctionResponse
    | Routers.System.DocAttributeResponse
    | Routers.System.DocModuleResponse
export class HeaderView implements VirtualDOM<HeadingLevel> {
    public readonly doc: Doc
    public readonly originPath: string
    public readonly withChildren: AnyVirtualDOM[]
    public readonly withClass: string
    public readonly text: string
    public readonly tag: HeadingLevel
    public readonly id: string
    public readonly class =
        'doc doc-heading d-flex flex-wrap align-items-center'
    public readonly children: ChildrenLike

    constructor(params: {
        text?: string
        tag: HeadingLevel
        withClass: string
        doc: Doc
        originPath: string
        withChildren?: AnyVirtualDOM[]
    }) {
        Object.assign(this, params)
        this.text = this.text || this.doc.name
        this.withChildren = this.withChildren || []
        this.id =
            this.doc.path.split('youwol.' + this.originPath + '.')[1] || ''
        this.children = [
            {
                tag: 'span',
                style: {
                    fontWeight: 'bolder',
                },
                class: `doc doc-object-name ${this.withClass}`,
                innerText: this.text,
            },
            ...this.withChildren,
        ]
    }
}
