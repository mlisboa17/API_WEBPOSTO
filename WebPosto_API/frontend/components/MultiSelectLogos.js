/**
 * MultiSelectLogos — filtro corporativo de empresas (Sprint F01.0).
 * Wrapper estável; implementação em EmpresaMultiselect.js.
 */
export {
  mountEmpresaMultiselect as mountMultiSelectLogos,
  updateEmpresaMultiselect as updateMultiSelectLogos,
  readEmpresaCodigoFromMultiselect as readEmpresaCodigoFromMultiSelectLogos,
  buildEmpresaCodigoFromSelection,
} from "./EmpresaMultiselect.js";
