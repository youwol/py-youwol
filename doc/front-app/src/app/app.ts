import { Router, Views, Node } from '@youwol/mkdocs-ts'
import { DockableTabs } from '@youwol/rx-tab-views'
import { BehaviorSubject } from 'rxjs'
import { VirtualDOM } from '@youwol/rx-vdom'
import { youwolInfo } from '../auto-generated-toml'

type Topic = 'DevPortal'

export class AppState extends Router {
    /**
     * @group State
     */
    public readonly bottomNavState: DockableTabs.State
    public readonly bottomNavTabs: Record<Topic, BottomNavTab>

    constructor(p) {
        super(p)
        this.bottomNavTabs = {
            DevPortal: new DevPortalTab(),
        }

        this.bottomNavState = new DockableTabs.State({
            disposition: 'bottom',
            viewState$: new BehaviorSubject<DockableTabs.DisplayMode>(
                'collapsed',
            ),
            tabs$: new BehaviorSubject(
                Object.values(this.bottomNavTabs).filter((d) => d != undefined),
            ),
            selected$: new BehaviorSubject<Topic>('DevPortal'),
            persistTabsView: true,
        })
    }
}

const height = '800px'
export class AppView extends Views.DefaultLayoutView {
    constructor({ appState }: { appState: AppState }) {
        super({
            router: appState,
            name: `YouWol#${youwolInfo.version}`, //new Views.TopBannerView({ name: 'YouWol' }),
        })

        const sideNav = new DockableTabs.View({
            state: appState.bottomNavState,
            styleOptions: {
                initialPanelSize: '350px',
                wrapper: { style: { minHeight: height } },
            },
        })
        this.children.push({
            tag: 'div',
            class: {
                source$: appState.currentNode$,
                vdomMap: (node: Node) => {
                    return node.name == "Publish a 'raw' app." ? '' : 'd-none'
                },
            },
            children: [sideNav],
        })
    }
}

/**
 * @category View
 */
class BottomNavTab extends DockableTabs.Tab {
    public readonly tag = 'div'
    public readonly defaultViewId: string
    public readonly defaultView: () => VirtualDOM<'div'>
    public readonly topic: Topic

    protected constructor(params: {
        topic: Topic
        defaultViewId: string
        defaultView: () => VirtualDOM<'div'>
        content: () => VirtualDOM<'div'>
        title: string
        icon: string
    }) {
        super({ ...params, id: params.topic })
        Object.assign(this, params)
    }
}

export class DevPortalTab extends BottomNavTab {
    constructor() {
        super({
            topic: 'DevPortal',
            title: 'DevPortal',
            icon: 'fas fa-globe',
            defaultViewId: 'dashboard',
            defaultView: () => {
                return { tag: 'div', innerText: 'Default view' }
            },
            content: () => {
                return {
                    tag: 'div',
                    style: { minHeight: '500px' },
                    children: [
                        {
                            tag: 'iframe',
                            src: '/applications/@youwol/developer-portal/latest',
                            height,
                            width: '100%',
                        },
                    ],
                }
            },
        })
    }
}
