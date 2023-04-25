import { VirtualDOM, attr$, render } from '@youwol/flux-view'
import { timer } from 'rxjs'

export {}

/**
 * @category View
 */
class ContentView implements VirtualDOM {
    /**
     * @group Immutable DOM constants
     */
    public readonly class =
        'fv-text-primary p-5 h-100 text-center d-flex flex-column justify-content-around'

    /**
     * @group Immutable DOM constants
     */
    public readonly children: VirtualDOM[]

    constructor() {
        this.children = [
            {
                children: [
                    {
                        innerText: attr$(
                            timer(0, 1000),
                            () => `⌚ ${new Date().toLocaleString()}`,
                        ),
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
                href: '',
                innerText: 'Find out more on writing apps',
            },
            {
                tag: 'a',
                href: '',
                innerText:
                    'The source code of the app & debug options are in the dev-tool of your browser',
            },
        ]
    }
}

document.getElementById('content').appendChild(render(new ContentView()))
