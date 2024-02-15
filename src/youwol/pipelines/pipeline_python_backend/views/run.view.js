class State {

  constructor({ triggerRun, project, flowId, stepId, rxjs, projectsRouter }) {

    this.triggerRun = triggerRun;
    this.projectsRouter = projectsRouter
    this.project = project
    this.flowId = flowId
    this.stepId = stepId
    this.rxjs = rxjs
    this.inputs$ = new rxjs.BehaviorSubject({})

    this.refresh()
    this.port$ = new rxjs.BehaviorSubject('auto')
    this.autoRun$ = new rxjs.BehaviorSubject(true)
    this.installDispatch$ = new rxjs.BehaviorSubject(true)
    const config$ = projectsRouter.getStepConfiguration$({
      projectId: project.id,
      flowId,
      stepId,
    });
    config$.subscribe((config) => {
      config = {autoRun: true, installDispatch: true, port:'auto', ...config}
      this.autoRun$.next(config.autoRun)
      this.installDispatch$.next(config.installDispatch)
      this.port$.next(config.port)
    });

  }


  run() {
    this.triggerRun({
      configuration: {
        autoRun: this.autoRun$.value,
        installDispatch: this.installDispatch$.value,
        port: this.port$.value
      },
    });
  }

  stop() {
    this.projectsRouter.executeStepGetCommand$({
      commandId: "stop_backend",
      projectId: this.project.id,
      flowId: this.flowId,
      stepId: this.stepId,
    }).subscribe(() => this.refresh())
  }

  refresh(){
    this.projectsRouter.executeStepGetCommand$({
      commandId: "get_info",
      projectId: this.project.id,
      flowId: this.flowId,
      stepId: this.stepId,
    }).subscribe(d => {
      this.inputs$.next(d)} )
  }
}

class RunningInstanceView{
  tag = "div";
  constructor(state, {pid, serverPid, port}) {
    this.children = [
      { tag:'div', innerText: 'Backend running:'},
      { tag:'ul', children:[
          {
            tag:'li',
            innerText:`port: ${port}`
          },
          {
            tag:'li',
            innerText:`pid: ${pid}`
          },
          {
            tag:'li',
            innerText:`server's pid: ${serverPid}`
          }
        ]
      },
      {
        tag: "div",
        class:'d-flex align-items-center  fv-pointer',
        children: [{
            tag:'i',
            class: "fas fa-stop",
          }],
        onclick: () => {
          state.stop()
        },
      }
    ]
  }
}

class CheckBoxView {

  tag = "div";
  class = 'd-flex align-items-center'
  constructor({title, subject$}){

    this.children = [
      {
        tag: "input",
        type:'checkbox',
        checked: {source$:subject$, vdomMap:(checked) => checked},
        onchange: (ev) => subject$.next(ev.target.checked)
      },
      {
        tag:'i', class:'mx-2'
      },
      {
        tag:'div',
        innerText:title,
      }]
  }
}

class PortView{
  tag = 'div'
  class = 'd-flex align-items-center'
  constructor(state, {project}){
    this.children = [
      {
        tag:'div',
        innerText: "Dispatch's port:",
        class:'mr-2'
      },
      { tag: 'select',
        onchange: (ev) => state.port$.next(ev.target.value),
        children:[
          { tag: 'option',
            innerText:'auto',
            selected: {source$:state.port$, vdomMap: (p) => p ==='auto' && 'selected'}
          },
          { tag: 'option',
            innerText:'default',
            selected: {source$:state.port$, vdomMap: (p) => p ==='default'&& 'selected'}
          }
        ]
      },
    ]
  }
}
class NewInstanceView{
  tag = "div";
  constructor(state, {project}) {
    this.children = [
      {
        tag: 'div',
        children:[
          new CheckBoxView({
            title: 'Start backend',
            subject$:state.autoRun$}),
          new CheckBoxView({
            title: `Install dispatch '/backends/${project.name}/${project.version}'`,
            subject$:state.installDispatch$}),
          new PortView(state, {project})
        ]
      },
      { tag: 'div', class:'my-2'},
      {
        tag: "div",
        class:'d-flex align-items-center fv-pointer border rounded p-1 fv-hover-text-focus',
        style:{
          width:'fit-content'
        },
        children: [
          {
            tag:'i',
            class: "fas fa-check fv-text-success mr-1",
          },{
            tag:'div',
            innerText: "Apply & run",
          }],
        onclick: () => {
          state.run()
        },
      },
    ]
  }
}


class ConfigView {
  tag = "div";
  class =
    "h-100 w-100 rounded yw-animate-in p-3";

  constructor({ state }) {
    this.children = [
      {
        source$: state.inputs$,
        vdomMap: (info) => {
          if(info.status === 404){
            return new NewInstanceView(state, {project: state.project})
          }
          return new RunningInstanceView(state,info)
        }
      },
    ];
  }
}

async function getView({
  triggerRun,
  project,
  flowId,
  stepId,
  projectsRouter,
  webpmClient,
}) {
  const { rxjs, rxVdom } = await webpmClient.install({
    modules: ["@youwol/rx-vdom#^1.0.1 as rxVdom", "rxjs#^7.5.6 as rxjs"],
  });
  const state = new State({
    triggerRun,
    project,
    flowId,
    stepId,
    rxjs,
    projectsRouter,
  });

  const vDom = new ConfigView({
    state,
  });

  return rxVdom.render(vDom);
}

// noinspection JSAnnotator
return getView;
