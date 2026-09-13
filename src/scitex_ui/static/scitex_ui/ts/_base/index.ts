/**
 * Base module — shared abstractions for scitex-ui components.
 */
export { BaseComponent } from "./BaseComponent";
export type { BaseComponentConfig } from "./types";
export {
  MOUNT_ATTRIBUTE,
  MOUNT_META_NAME,
  MountPrefixMissingError,
  apiUrl,
  mountPrefix,
} from "./mount";
export {
  APP_SCOPE_META_NAME,
  SCOPE_USER,
  SCOPE_PROJECT,
  AppScopeMarkerInvalidError,
  appScope,
  mayOfferProjectSelector,
} from "./scope";
export type { AppScope } from "./scope";
