import { VirtualDOM, render, ChildrenLike } from '@youwol/rx-vdom'
import { timer } from 'rxjs'

export {}

/**
 * @category View
 */
class ContentView implements VirtualDOM<'div'> {
    /**
     * @group Immutable DOM constants
     */
    public readonly tag = 'div'

    /**
     * @group Immutable DOM constants
     */
    public readonly class =
        'fv-text-primary p-5 h-100 text-center d-flex flex-column justify-content-around'

    /**
     * @group Immutable DOM constants
     */
    public readonly children: ChildrenLike

    constructor() {
        this.children = [
            {   tag: 'div',
                children: [
                    {   tag: 'div',
                        innerText: {
                            source$:timer(0, 1000),
                            vdomMap: () => `⌚ ${new Date().toLocaleString()}`,
                        },
                    },
                    {
                        tag: 'h1',
                        innerText:
                            '🎉 Your app has been successfully published 🎉',
                    },
                ],
            },
            {
                tag: 'a',
                href: 'https://l.youwol.com/doc/py-youwol',
                innerText: 'How to use py-youwol & the dev. portal',
            },
            {
                tag: 'a',
                href: 'https://l.youwol.com/doc/@youwol/rx-vdom',
                innerText:
                    'How to write applications with @youwol/rx-vdom',
            },
        ]
    }
}

document.getElementById('content').appendChild(render(new ContentView()))
