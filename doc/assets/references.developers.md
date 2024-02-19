# Developers section

## Documentation

### Why not `mkdocs` & `griffe`

The main limitations are:

- It is built on markdown => Not everything is markdown, but javascript easily includes markdown
  (e.g. think of `@youwol/explorer` application)
- Navigation needs to be known in advance => not always the case (e.g. here, `@youwol/explorer`, etc )
- Can not compose documentation
- Some links regarding types in python are missing (attribute)

The main additional values:

- Check path for internal links.
  Idea: provide a TS 'Navigation' interface to make sure all links are correct (using TS typesystem)
- Multiple plugins for 'widgets' (e.g. annotations, lines highlighting, etc). To be provided when needed.

### Why not stories

The main limitations are:

- No source control
- No navigation system using proper router
- Maintenance difficult because of 'drag & drop API'
- A lot of limitations

### Magic in markdowns

<!-- by default the anchor is 'some-examples' if need be additional anchors can be defined:
<div id='examples0'></div>
-->

you can use factorized custom widget:

<some-id param0="" param1=""></some-id>

you can use custom view inside a code block of type `custom-view` :

```javascript
return async ({ webpm }) => {
  const { rxjs } = await webpm.install({ modules: ['rxjs#^7.5.6 as rxjs'] })
  // can also return HTMLElement
  return {
    tag: 'div',
    innerText: {
      source$: rxjs.timer(0, 1000),
      vdomMap: () => new Date().toLocaleTimeString(),
    },
  }
}
```

Produces the following outputs:

```custom-view
return async ({webpm}) => {
    const {rxjs} = await webpm.install({modules:['rxjs#^7.5.6 as rxjs']})

    return {
        innerText: {
            source$:rxjs.timer(0,1000),
            vdomMap: () => new Date().toLocaleTimeString()
        }
    }
}
```

### Links

For internal navigation (for static checking):

For linking, use `@nav` top prefix URL in links:
`[foo](@nav/how-to)`

Inside py-youwol,

<!--
We need a tool to ensure that the following link resolve.

-->

Please see this [page](@nav/how-to)

Or also this [one](@nav/how-to/install-youwol)

## In py-youwol

To reference in docstring other members:

- **Class** : For a class, use prefix `yw-nav-class` in link, e.g.:

  `[foo](@yw-nav-class:...models_config.AuthorizationProvider)`

- **Attribute** : For attribute of a class (variable or member), use prefix `yw-nav-attr` in link, e.g.:

`[foo](@yw-nav-attr:...models_config.RecursiveProjectsFinder.fromPaths)`

- **Function** : Global function, use prefix `yw-nav-func` in link, e.g.:

  `[foo](@yw-nav-func:...models.defaults.default_auth_provider)`

- **Variable** : Global variable , use prefix `yw-nav-var` in link, e.g.:

  `[foo](@yw-nav-var:...models.defaults.default_path_cache_dir)`

Do not rely on type inference, remember to annotate:

- return type of function
- global variables

### Problems

- The links generated in py-youwol for type that references aliases are not correct

### TODO

- How we can do a static check of the validity of all the internal navigation of a document
- How we can integrate typedoc documentation

## Comparison with mkdocs & mkdocstring

In mkdocs:

- ✅ mkdocs better output some elements and have more capabilities regarding display (e.g. display annotation, highlights lines, ...).
  But this could be easily added in our solution
- ❌ mkdocs is base on markdown. It is possible to do customization, but cumbersome (jinja templating, add scripts).
  It has (strong) limitations in terms of flexibility.
- ❌ document organization should be known in advance. E.g. the modules organization has to be manually rewritten
- ❌ missing automatic code introspection (attribute type, inherited by).

Our solution:

- ✅ document organization can be created on-the-fly (e.g. auto created using modules organization)
- ✅ customization of the doc in our solution is much higher, also, thanks to typescript, easy to find out what is needed.
  (e.g. how to render class, function, TOC, defining layout, etc). At the end it is just a plain application,
  control over dependencies fetching (e.g. at start, when navigating to a page), layout can be anything, and more.
- ✅ in markdown it is easy to include custom view using javascript code
- ✅ attribute type are auto-linked, 'inherited by' provided
- ✅ we can do whatever we want
- ✅ just a regular project managed by the TS pipeline (e.g. devserver working out of the box)
- ❌ Some display options in markdown (e.g. display annotation, highlights lines, ...) remains to be implemented

# TODO

## Rename route

Environment:

- configuration => environment

System:

- folder_content => query_folder_content
- get_logs => query_logs
- query_logs => query_root_logs

## others
