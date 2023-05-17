import * as AllImports from "{{name}}";
import DefaultImport from "{{name}}";

export * from "{{name}}";
export default DefaultImport;
// Pick the right one and remove useless import
window["{{exportedSymbol}}_APIv{{apiVersion}}"] = DefaultImport || AllImports;
