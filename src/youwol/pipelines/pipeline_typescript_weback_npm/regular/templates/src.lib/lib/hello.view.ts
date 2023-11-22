import { VirtualDOM, ChildrenLike } from '@youwol/rx-vdom'
import { timer } from 'rxjs'

/**
 * @category View
 */
export class HelloView implements VirtualDOM<'div'> {
    /**
     * @group Immutable DOM Constants
     */
    public readonly tag = 'div'
    /**
     * @group Immutable DOM Constants
     */
    public readonly class =
        'p-2 m-2 d-flex justify-content-center align-items-center'

    /**
     * @group Immutable DOM Constants
     */
    public readonly children: ChildrenLike

    constructor() {
        this.children = [
            { tag: 'div', class: 'fas fa-clock mx-1' },
            {
                tag: 'div',
                innerText: {
                    source$: timer(0, 1000),
                    vdomMap: (_count) =>
                        `Hello :), it is: ${new Date().toLocaleString()}`,
                }
            },
        ]
    }
}
