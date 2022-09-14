import { VirtualDOM, attr$ } from '@youwol/flux-view'
import { timer } from 'rxjs'

/**
 * @category View
 */
export class HelloView implements VirtualDOM {
    /**
     * @group Immutable DOM Constants
     */
    public readonly class =
        'p-2 m-2 d-flex justify-content-center align-items-center'

    /**
     * @group Immutable DOM Constants
     */
    public readonly children: VirtualDOM[]

    constructor() {
        this.children = [
            {
                class: 'fas fa-clock mx-1',
            },
            {
                innerText: attr$(
                    timer(0, 1000),
                    (_count) =>
                        `Hello :), it is: ${new Date().toLocaleString()}`,
                ),
            },
        ]
    }
}
