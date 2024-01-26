type AllTags = keyof HTMLElementTagNameMap
export type Configuration = {
    TypeCheck: 'strict'
    SupportedHTMLTags: 'Dev' extends 'Prod' ? AllTags : DevTags
    WithFluxView: false
}

type DevTags =
    | 'div'
    | 'a'
    | 'h1'
    | 'h2'
    | 'h3'
    | 'h4'
    | 'iframe'
    | 'i'
    | 'ul'
    | 'li'
    | 'span'
    | 'pre'
    | 'footer'
