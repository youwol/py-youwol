import { render } from '@youwol/rx-vdom'
import { navigation } from './navigation'
import { AppState, AppView } from './app'
import { setup } from '../auto-generated'

const appState = new AppState({
    navigation,
    basePath: `/applications/${setup.name}/${setup.version}`,
})

document
    .getElementById('content')
    .appendChild(render(new AppView({ appState })))
