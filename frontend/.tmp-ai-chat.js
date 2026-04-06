(() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // node_modules/react/cjs/react.development.js
  var require_react_development = __commonJS({
    "node_modules/react/cjs/react.development.js"(exports, module) {
      "use strict";
      if (true) {
        (function() {
          "use strict";
          if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ !== "undefined" && typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStart === "function") {
            __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStart(new Error());
          }
          var ReactVersion = "18.3.1";
          var REACT_ELEMENT_TYPE = Symbol.for("react.element");
          var REACT_PORTAL_TYPE = Symbol.for("react.portal");
          var REACT_FRAGMENT_TYPE = Symbol.for("react.fragment");
          var REACT_STRICT_MODE_TYPE = Symbol.for("react.strict_mode");
          var REACT_PROFILER_TYPE = Symbol.for("react.profiler");
          var REACT_PROVIDER_TYPE = Symbol.for("react.provider");
          var REACT_CONTEXT_TYPE = Symbol.for("react.context");
          var REACT_FORWARD_REF_TYPE = Symbol.for("react.forward_ref");
          var REACT_SUSPENSE_TYPE = Symbol.for("react.suspense");
          var REACT_SUSPENSE_LIST_TYPE = Symbol.for("react.suspense_list");
          var REACT_MEMO_TYPE = Symbol.for("react.memo");
          var REACT_LAZY_TYPE = Symbol.for("react.lazy");
          var REACT_OFFSCREEN_TYPE = Symbol.for("react.offscreen");
          var MAYBE_ITERATOR_SYMBOL = Symbol.iterator;
          var FAUX_ITERATOR_SYMBOL = "@@iterator";
          function getIteratorFn(maybeIterable) {
            if (maybeIterable === null || typeof maybeIterable !== "object") {
              return null;
            }
            var maybeIterator = MAYBE_ITERATOR_SYMBOL && maybeIterable[MAYBE_ITERATOR_SYMBOL] || maybeIterable[FAUX_ITERATOR_SYMBOL];
            if (typeof maybeIterator === "function") {
              return maybeIterator;
            }
            return null;
          }
          var ReactCurrentDispatcher = {
            /**
             * @internal
             * @type {ReactComponent}
             */
            current: null
          };
          var ReactCurrentBatchConfig = {
            transition: null
          };
          var ReactCurrentActQueue = {
            current: null,
            // Used to reproduce behavior of `batchedUpdates` in legacy mode.
            isBatchingLegacy: false,
            didScheduleLegacyUpdate: false
          };
          var ReactCurrentOwner = {
            /**
             * @internal
             * @type {ReactComponent}
             */
            current: null
          };
          var ReactDebugCurrentFrame = {};
          var currentExtraStackFrame = null;
          function setExtraStackFrame(stack) {
            {
              currentExtraStackFrame = stack;
            }
          }
          {
            ReactDebugCurrentFrame.setExtraStackFrame = function(stack) {
              {
                currentExtraStackFrame = stack;
              }
            };
            ReactDebugCurrentFrame.getCurrentStack = null;
            ReactDebugCurrentFrame.getStackAddendum = function() {
              var stack = "";
              if (currentExtraStackFrame) {
                stack += currentExtraStackFrame;
              }
              var impl = ReactDebugCurrentFrame.getCurrentStack;
              if (impl) {
                stack += impl() || "";
              }
              return stack;
            };
          }
          var enableScopeAPI = false;
          var enableCacheElement = false;
          var enableTransitionTracing = false;
          var enableLegacyHidden = false;
          var enableDebugTracing = false;
          var ReactSharedInternals = {
            ReactCurrentDispatcher,
            ReactCurrentBatchConfig,
            ReactCurrentOwner
          };
          {
            ReactSharedInternals.ReactDebugCurrentFrame = ReactDebugCurrentFrame;
            ReactSharedInternals.ReactCurrentActQueue = ReactCurrentActQueue;
          }
          function warn(format) {
            {
              {
                for (var _len = arguments.length, args = new Array(_len > 1 ? _len - 1 : 0), _key = 1; _key < _len; _key++) {
                  args[_key - 1] = arguments[_key];
                }
                printWarning("warn", format, args);
              }
            }
          }
          function error(format) {
            {
              {
                for (var _len2 = arguments.length, args = new Array(_len2 > 1 ? _len2 - 1 : 0), _key2 = 1; _key2 < _len2; _key2++) {
                  args[_key2 - 1] = arguments[_key2];
                }
                printWarning("error", format, args);
              }
            }
          }
          function printWarning(level, format, args) {
            {
              var ReactDebugCurrentFrame2 = ReactSharedInternals.ReactDebugCurrentFrame;
              var stack = ReactDebugCurrentFrame2.getStackAddendum();
              if (stack !== "") {
                format += "%s";
                args = args.concat([stack]);
              }
              var argsWithFormat = args.map(function(item) {
                return String(item);
              });
              argsWithFormat.unshift("Warning: " + format);
              Function.prototype.apply.call(console[level], console, argsWithFormat);
            }
          }
          var didWarnStateUpdateForUnmountedComponent = {};
          function warnNoop(publicInstance, callerName) {
            {
              var _constructor = publicInstance.constructor;
              var componentName = _constructor && (_constructor.displayName || _constructor.name) || "ReactClass";
              var warningKey = componentName + "." + callerName;
              if (didWarnStateUpdateForUnmountedComponent[warningKey]) {
                return;
              }
              error("Can't call %s on a component that is not yet mounted. This is a no-op, but it might indicate a bug in your application. Instead, assign to `this.state` directly or define a `state = {};` class property with the desired state in the %s component.", callerName, componentName);
              didWarnStateUpdateForUnmountedComponent[warningKey] = true;
            }
          }
          var ReactNoopUpdateQueue = {
            /**
             * Checks whether or not this composite component is mounted.
             * @param {ReactClass} publicInstance The instance we want to test.
             * @return {boolean} True if mounted, false otherwise.
             * @protected
             * @final
             */
            isMounted: function(publicInstance) {
              return false;
            },
            /**
             * Forces an update. This should only be invoked when it is known with
             * certainty that we are **not** in a DOM transaction.
             *
             * You may want to call this when you know that some deeper aspect of the
             * component's state has changed but `setState` was not called.
             *
             * This will not invoke `shouldComponentUpdate`, but it will invoke
             * `componentWillUpdate` and `componentDidUpdate`.
             *
             * @param {ReactClass} publicInstance The instance that should rerender.
             * @param {?function} callback Called after component is updated.
             * @param {?string} callerName name of the calling function in the public API.
             * @internal
             */
            enqueueForceUpdate: function(publicInstance, callback, callerName) {
              warnNoop(publicInstance, "forceUpdate");
            },
            /**
             * Replaces all of the state. Always use this or `setState` to mutate state.
             * You should treat `this.state` as immutable.
             *
             * There is no guarantee that `this.state` will be immediately updated, so
             * accessing `this.state` after calling this method may return the old value.
             *
             * @param {ReactClass} publicInstance The instance that should rerender.
             * @param {object} completeState Next state.
             * @param {?function} callback Called after component is updated.
             * @param {?string} callerName name of the calling function in the public API.
             * @internal
             */
            enqueueReplaceState: function(publicInstance, completeState, callback, callerName) {
              warnNoop(publicInstance, "replaceState");
            },
            /**
             * Sets a subset of the state. This only exists because _pendingState is
             * internal. This provides a merging strategy that is not available to deep
             * properties which is confusing. TODO: Expose pendingState or don't use it
             * during the merge.
             *
             * @param {ReactClass} publicInstance The instance that should rerender.
             * @param {object} partialState Next partial state to be merged with state.
             * @param {?function} callback Called after component is updated.
             * @param {?string} Name of the calling function in the public API.
             * @internal
             */
            enqueueSetState: function(publicInstance, partialState, callback, callerName) {
              warnNoop(publicInstance, "setState");
            }
          };
          var assign = Object.assign;
          var emptyObject = {};
          {
            Object.freeze(emptyObject);
          }
          function Component(props, context, updater) {
            this.props = props;
            this.context = context;
            this.refs = emptyObject;
            this.updater = updater || ReactNoopUpdateQueue;
          }
          Component.prototype.isReactComponent = {};
          Component.prototype.setState = function(partialState, callback) {
            if (typeof partialState !== "object" && typeof partialState !== "function" && partialState != null) {
              throw new Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");
            }
            this.updater.enqueueSetState(this, partialState, callback, "setState");
          };
          Component.prototype.forceUpdate = function(callback) {
            this.updater.enqueueForceUpdate(this, callback, "forceUpdate");
          };
          {
            var deprecatedAPIs = {
              isMounted: ["isMounted", "Instead, make sure to clean up subscriptions and pending requests in componentWillUnmount to prevent memory leaks."],
              replaceState: ["replaceState", "Refactor your code to use setState instead (see https://github.com/facebook/react/issues/3236)."]
            };
            var defineDeprecationWarning = function(methodName, info) {
              Object.defineProperty(Component.prototype, methodName, {
                get: function() {
                  warn("%s(...) is deprecated in plain JavaScript React classes. %s", info[0], info[1]);
                  return void 0;
                }
              });
            };
            for (var fnName in deprecatedAPIs) {
              if (deprecatedAPIs.hasOwnProperty(fnName)) {
                defineDeprecationWarning(fnName, deprecatedAPIs[fnName]);
              }
            }
          }
          function ComponentDummy() {
          }
          ComponentDummy.prototype = Component.prototype;
          function PureComponent(props, context, updater) {
            this.props = props;
            this.context = context;
            this.refs = emptyObject;
            this.updater = updater || ReactNoopUpdateQueue;
          }
          var pureComponentPrototype = PureComponent.prototype = new ComponentDummy();
          pureComponentPrototype.constructor = PureComponent;
          assign(pureComponentPrototype, Component.prototype);
          pureComponentPrototype.isPureReactComponent = true;
          function createRef() {
            var refObject = {
              current: null
            };
            {
              Object.seal(refObject);
            }
            return refObject;
          }
          var isArrayImpl = Array.isArray;
          function isArray(a) {
            return isArrayImpl(a);
          }
          function typeName(value) {
            {
              var hasToStringTag = typeof Symbol === "function" && Symbol.toStringTag;
              var type = hasToStringTag && value[Symbol.toStringTag] || value.constructor.name || "Object";
              return type;
            }
          }
          function willCoercionThrow(value) {
            {
              try {
                testStringCoercion(value);
                return false;
              } catch (e) {
                return true;
              }
            }
          }
          function testStringCoercion(value) {
            return "" + value;
          }
          function checkKeyStringCoercion(value) {
            {
              if (willCoercionThrow(value)) {
                error("The provided key is an unsupported type %s. This value must be coerced to a string before before using it here.", typeName(value));
                return testStringCoercion(value);
              }
            }
          }
          function getWrappedName(outerType, innerType, wrapperName) {
            var displayName = outerType.displayName;
            if (displayName) {
              return displayName;
            }
            var functionName = innerType.displayName || innerType.name || "";
            return functionName !== "" ? wrapperName + "(" + functionName + ")" : wrapperName;
          }
          function getContextName(type) {
            return type.displayName || "Context";
          }
          function getComponentNameFromType(type) {
            if (type == null) {
              return null;
            }
            {
              if (typeof type.tag === "number") {
                error("Received an unexpected object in getComponentNameFromType(). This is likely a bug in React. Please file an issue.");
              }
            }
            if (typeof type === "function") {
              return type.displayName || type.name || null;
            }
            if (typeof type === "string") {
              return type;
            }
            switch (type) {
              case REACT_FRAGMENT_TYPE:
                return "Fragment";
              case REACT_PORTAL_TYPE:
                return "Portal";
              case REACT_PROFILER_TYPE:
                return "Profiler";
              case REACT_STRICT_MODE_TYPE:
                return "StrictMode";
              case REACT_SUSPENSE_TYPE:
                return "Suspense";
              case REACT_SUSPENSE_LIST_TYPE:
                return "SuspenseList";
            }
            if (typeof type === "object") {
              switch (type.$$typeof) {
                case REACT_CONTEXT_TYPE:
                  var context = type;
                  return getContextName(context) + ".Consumer";
                case REACT_PROVIDER_TYPE:
                  var provider = type;
                  return getContextName(provider._context) + ".Provider";
                case REACT_FORWARD_REF_TYPE:
                  return getWrappedName(type, type.render, "ForwardRef");
                case REACT_MEMO_TYPE:
                  var outerName = type.displayName || null;
                  if (outerName !== null) {
                    return outerName;
                  }
                  return getComponentNameFromType(type.type) || "Memo";
                case REACT_LAZY_TYPE: {
                  var lazyComponent = type;
                  var payload = lazyComponent._payload;
                  var init = lazyComponent._init;
                  try {
                    return getComponentNameFromType(init(payload));
                  } catch (x) {
                    return null;
                  }
                }
              }
            }
            return null;
          }
          var hasOwnProperty = Object.prototype.hasOwnProperty;
          var RESERVED_PROPS = {
            key: true,
            ref: true,
            __self: true,
            __source: true
          };
          var specialPropKeyWarningShown, specialPropRefWarningShown, didWarnAboutStringRefs;
          {
            didWarnAboutStringRefs = {};
          }
          function hasValidRef(config) {
            {
              if (hasOwnProperty.call(config, "ref")) {
                var getter = Object.getOwnPropertyDescriptor(config, "ref").get;
                if (getter && getter.isReactWarning) {
                  return false;
                }
              }
            }
            return config.ref !== void 0;
          }
          function hasValidKey(config) {
            {
              if (hasOwnProperty.call(config, "key")) {
                var getter = Object.getOwnPropertyDescriptor(config, "key").get;
                if (getter && getter.isReactWarning) {
                  return false;
                }
              }
            }
            return config.key !== void 0;
          }
          function defineKeyPropWarningGetter(props, displayName) {
            var warnAboutAccessingKey = function() {
              {
                if (!specialPropKeyWarningShown) {
                  specialPropKeyWarningShown = true;
                  error("%s: `key` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", displayName);
                }
              }
            };
            warnAboutAccessingKey.isReactWarning = true;
            Object.defineProperty(props, "key", {
              get: warnAboutAccessingKey,
              configurable: true
            });
          }
          function defineRefPropWarningGetter(props, displayName) {
            var warnAboutAccessingRef = function() {
              {
                if (!specialPropRefWarningShown) {
                  specialPropRefWarningShown = true;
                  error("%s: `ref` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", displayName);
                }
              }
            };
            warnAboutAccessingRef.isReactWarning = true;
            Object.defineProperty(props, "ref", {
              get: warnAboutAccessingRef,
              configurable: true
            });
          }
          function warnIfStringRefCannotBeAutoConverted(config) {
            {
              if (typeof config.ref === "string" && ReactCurrentOwner.current && config.__self && ReactCurrentOwner.current.stateNode !== config.__self) {
                var componentName = getComponentNameFromType(ReactCurrentOwner.current.type);
                if (!didWarnAboutStringRefs[componentName]) {
                  error('Component "%s" contains the string ref "%s". Support for string refs will be removed in a future major release. This case cannot be automatically converted to an arrow function. We ask you to manually fix this case by using useRef() or createRef() instead. Learn more about using refs safely here: https://reactjs.org/link/strict-mode-string-ref', componentName, config.ref);
                  didWarnAboutStringRefs[componentName] = true;
                }
              }
            }
          }
          var ReactElement = function(type, key, ref, self2, source, owner, props) {
            var element = {
              // This tag allows us to uniquely identify this as a React Element
              $$typeof: REACT_ELEMENT_TYPE,
              // Built-in properties that belong on the element
              type,
              key,
              ref,
              props,
              // Record the component responsible for creating this element.
              _owner: owner
            };
            {
              element._store = {};
              Object.defineProperty(element._store, "validated", {
                configurable: false,
                enumerable: false,
                writable: true,
                value: false
              });
              Object.defineProperty(element, "_self", {
                configurable: false,
                enumerable: false,
                writable: false,
                value: self2
              });
              Object.defineProperty(element, "_source", {
                configurable: false,
                enumerable: false,
                writable: false,
                value: source
              });
              if (Object.freeze) {
                Object.freeze(element.props);
                Object.freeze(element);
              }
            }
            return element;
          };
          function createElement(type, config, children) {
            var propName;
            var props = {};
            var key = null;
            var ref = null;
            var self2 = null;
            var source = null;
            if (config != null) {
              if (hasValidRef(config)) {
                ref = config.ref;
                {
                  warnIfStringRefCannotBeAutoConverted(config);
                }
              }
              if (hasValidKey(config)) {
                {
                  checkKeyStringCoercion(config.key);
                }
                key = "" + config.key;
              }
              self2 = config.__self === void 0 ? null : config.__self;
              source = config.__source === void 0 ? null : config.__source;
              for (propName in config) {
                if (hasOwnProperty.call(config, propName) && !RESERVED_PROPS.hasOwnProperty(propName)) {
                  props[propName] = config[propName];
                }
              }
            }
            var childrenLength = arguments.length - 2;
            if (childrenLength === 1) {
              props.children = children;
            } else if (childrenLength > 1) {
              var childArray = Array(childrenLength);
              for (var i = 0; i < childrenLength; i++) {
                childArray[i] = arguments[i + 2];
              }
              {
                if (Object.freeze) {
                  Object.freeze(childArray);
                }
              }
              props.children = childArray;
            }
            if (type && type.defaultProps) {
              var defaultProps = type.defaultProps;
              for (propName in defaultProps) {
                if (props[propName] === void 0) {
                  props[propName] = defaultProps[propName];
                }
              }
            }
            {
              if (key || ref) {
                var displayName = typeof type === "function" ? type.displayName || type.name || "Unknown" : type;
                if (key) {
                  defineKeyPropWarningGetter(props, displayName);
                }
                if (ref) {
                  defineRefPropWarningGetter(props, displayName);
                }
              }
            }
            return ReactElement(type, key, ref, self2, source, ReactCurrentOwner.current, props);
          }
          function cloneAndReplaceKey(oldElement, newKey) {
            var newElement = ReactElement(oldElement.type, newKey, oldElement.ref, oldElement._self, oldElement._source, oldElement._owner, oldElement.props);
            return newElement;
          }
          function cloneElement(element, config, children) {
            if (element === null || element === void 0) {
              throw new Error("React.cloneElement(...): The argument must be a React element, but you passed " + element + ".");
            }
            var propName;
            var props = assign({}, element.props);
            var key = element.key;
            var ref = element.ref;
            var self2 = element._self;
            var source = element._source;
            var owner = element._owner;
            if (config != null) {
              if (hasValidRef(config)) {
                ref = config.ref;
                owner = ReactCurrentOwner.current;
              }
              if (hasValidKey(config)) {
                {
                  checkKeyStringCoercion(config.key);
                }
                key = "" + config.key;
              }
              var defaultProps;
              if (element.type && element.type.defaultProps) {
                defaultProps = element.type.defaultProps;
              }
              for (propName in config) {
                if (hasOwnProperty.call(config, propName) && !RESERVED_PROPS.hasOwnProperty(propName)) {
                  if (config[propName] === void 0 && defaultProps !== void 0) {
                    props[propName] = defaultProps[propName];
                  } else {
                    props[propName] = config[propName];
                  }
                }
              }
            }
            var childrenLength = arguments.length - 2;
            if (childrenLength === 1) {
              props.children = children;
            } else if (childrenLength > 1) {
              var childArray = Array(childrenLength);
              for (var i = 0; i < childrenLength; i++) {
                childArray[i] = arguments[i + 2];
              }
              props.children = childArray;
            }
            return ReactElement(element.type, key, ref, self2, source, owner, props);
          }
          function isValidElement(object) {
            return typeof object === "object" && object !== null && object.$$typeof === REACT_ELEMENT_TYPE;
          }
          var SEPARATOR = ".";
          var SUBSEPARATOR = ":";
          function escape(key) {
            var escapeRegex = /[=:]/g;
            var escaperLookup = {
              "=": "=0",
              ":": "=2"
            };
            var escapedString = key.replace(escapeRegex, function(match) {
              return escaperLookup[match];
            });
            return "$" + escapedString;
          }
          var didWarnAboutMaps = false;
          var userProvidedKeyEscapeRegex = /\/+/g;
          function escapeUserProvidedKey(text) {
            return text.replace(userProvidedKeyEscapeRegex, "$&/");
          }
          function getElementKey(element, index) {
            if (typeof element === "object" && element !== null && element.key != null) {
              {
                checkKeyStringCoercion(element.key);
              }
              return escape("" + element.key);
            }
            return index.toString(36);
          }
          function mapIntoArray(children, array, escapedPrefix, nameSoFar, callback) {
            var type = typeof children;
            if (type === "undefined" || type === "boolean") {
              children = null;
            }
            var invokeCallback = false;
            if (children === null) {
              invokeCallback = true;
            } else {
              switch (type) {
                case "string":
                case "number":
                  invokeCallback = true;
                  break;
                case "object":
                  switch (children.$$typeof) {
                    case REACT_ELEMENT_TYPE:
                    case REACT_PORTAL_TYPE:
                      invokeCallback = true;
                  }
              }
            }
            if (invokeCallback) {
              var _child = children;
              var mappedChild = callback(_child);
              var childKey = nameSoFar === "" ? SEPARATOR + getElementKey(_child, 0) : nameSoFar;
              if (isArray(mappedChild)) {
                var escapedChildKey = "";
                if (childKey != null) {
                  escapedChildKey = escapeUserProvidedKey(childKey) + "/";
                }
                mapIntoArray(mappedChild, array, escapedChildKey, "", function(c) {
                  return c;
                });
              } else if (mappedChild != null) {
                if (isValidElement(mappedChild)) {
                  {
                    if (mappedChild.key && (!_child || _child.key !== mappedChild.key)) {
                      checkKeyStringCoercion(mappedChild.key);
                    }
                  }
                  mappedChild = cloneAndReplaceKey(
                    mappedChild,
                    // Keep both the (mapped) and old keys if they differ, just as
                    // traverseAllChildren used to do for objects as children
                    escapedPrefix + // $FlowFixMe Flow incorrectly thinks React.Portal doesn't have a key
                    (mappedChild.key && (!_child || _child.key !== mappedChild.key) ? (
                      // $FlowFixMe Flow incorrectly thinks existing element's key can be a number
                      // eslint-disable-next-line react-internal/safe-string-coercion
                      escapeUserProvidedKey("" + mappedChild.key) + "/"
                    ) : "") + childKey
                  );
                }
                array.push(mappedChild);
              }
              return 1;
            }
            var child;
            var nextName;
            var subtreeCount = 0;
            var nextNamePrefix = nameSoFar === "" ? SEPARATOR : nameSoFar + SUBSEPARATOR;
            if (isArray(children)) {
              for (var i = 0; i < children.length; i++) {
                child = children[i];
                nextName = nextNamePrefix + getElementKey(child, i);
                subtreeCount += mapIntoArray(child, array, escapedPrefix, nextName, callback);
              }
            } else {
              var iteratorFn = getIteratorFn(children);
              if (typeof iteratorFn === "function") {
                var iterableChildren = children;
                {
                  if (iteratorFn === iterableChildren.entries) {
                    if (!didWarnAboutMaps) {
                      warn("Using Maps as children is not supported. Use an array of keyed ReactElements instead.");
                    }
                    didWarnAboutMaps = true;
                  }
                }
                var iterator = iteratorFn.call(iterableChildren);
                var step;
                var ii = 0;
                while (!(step = iterator.next()).done) {
                  child = step.value;
                  nextName = nextNamePrefix + getElementKey(child, ii++);
                  subtreeCount += mapIntoArray(child, array, escapedPrefix, nextName, callback);
                }
              } else if (type === "object") {
                var childrenString = String(children);
                throw new Error("Objects are not valid as a React child (found: " + (childrenString === "[object Object]" ? "object with keys {" + Object.keys(children).join(", ") + "}" : childrenString) + "). If you meant to render a collection of children, use an array instead.");
              }
            }
            return subtreeCount;
          }
          function mapChildren(children, func, context) {
            if (children == null) {
              return children;
            }
            var result = [];
            var count = 0;
            mapIntoArray(children, result, "", "", function(child) {
              return func.call(context, child, count++);
            });
            return result;
          }
          function countChildren(children) {
            var n = 0;
            mapChildren(children, function() {
              n++;
            });
            return n;
          }
          function forEachChildren(children, forEachFunc, forEachContext) {
            mapChildren(children, function() {
              forEachFunc.apply(this, arguments);
            }, forEachContext);
          }
          function toArray(children) {
            return mapChildren(children, function(child) {
              return child;
            }) || [];
          }
          function onlyChild(children) {
            if (!isValidElement(children)) {
              throw new Error("React.Children.only expected to receive a single React element child.");
            }
            return children;
          }
          function createContext4(defaultValue) {
            var context = {
              $$typeof: REACT_CONTEXT_TYPE,
              // As a workaround to support multiple concurrent renderers, we categorize
              // some renderers as primary and others as secondary. We only expect
              // there to be two concurrent renderers at most: React Native (primary) and
              // Fabric (secondary); React DOM (primary) and React ART (secondary).
              // Secondary renderers store their context values on separate fields.
              _currentValue: defaultValue,
              _currentValue2: defaultValue,
              // Used to track how many concurrent renderers this context currently
              // supports within in a single renderer. Such as parallel server rendering.
              _threadCount: 0,
              // These are circular
              Provider: null,
              Consumer: null,
              // Add these to use same hidden class in VM as ServerContext
              _defaultValue: null,
              _globalName: null
            };
            context.Provider = {
              $$typeof: REACT_PROVIDER_TYPE,
              _context: context
            };
            var hasWarnedAboutUsingNestedContextConsumers = false;
            var hasWarnedAboutUsingConsumerProvider = false;
            var hasWarnedAboutDisplayNameOnConsumer = false;
            {
              var Consumer = {
                $$typeof: REACT_CONTEXT_TYPE,
                _context: context
              };
              Object.defineProperties(Consumer, {
                Provider: {
                  get: function() {
                    if (!hasWarnedAboutUsingConsumerProvider) {
                      hasWarnedAboutUsingConsumerProvider = true;
                      error("Rendering <Context.Consumer.Provider> is not supported and will be removed in a future major release. Did you mean to render <Context.Provider> instead?");
                    }
                    return context.Provider;
                  },
                  set: function(_Provider) {
                    context.Provider = _Provider;
                  }
                },
                _currentValue: {
                  get: function() {
                    return context._currentValue;
                  },
                  set: function(_currentValue) {
                    context._currentValue = _currentValue;
                  }
                },
                _currentValue2: {
                  get: function() {
                    return context._currentValue2;
                  },
                  set: function(_currentValue2) {
                    context._currentValue2 = _currentValue2;
                  }
                },
                _threadCount: {
                  get: function() {
                    return context._threadCount;
                  },
                  set: function(_threadCount) {
                    context._threadCount = _threadCount;
                  }
                },
                Consumer: {
                  get: function() {
                    if (!hasWarnedAboutUsingNestedContextConsumers) {
                      hasWarnedAboutUsingNestedContextConsumers = true;
                      error("Rendering <Context.Consumer.Consumer> is not supported and will be removed in a future major release. Did you mean to render <Context.Consumer> instead?");
                    }
                    return context.Consumer;
                  }
                },
                displayName: {
                  get: function() {
                    return context.displayName;
                  },
                  set: function(displayName) {
                    if (!hasWarnedAboutDisplayNameOnConsumer) {
                      warn("Setting `displayName` on Context.Consumer has no effect. You should set it directly on the context with Context.displayName = '%s'.", displayName);
                      hasWarnedAboutDisplayNameOnConsumer = true;
                    }
                  }
                }
              });
              context.Consumer = Consumer;
            }
            {
              context._currentRenderer = null;
              context._currentRenderer2 = null;
            }
            return context;
          }
          var Uninitialized = -1;
          var Pending = 0;
          var Resolved = 1;
          var Rejected = 2;
          function lazyInitializer(payload) {
            if (payload._status === Uninitialized) {
              var ctor = payload._result;
              var thenable = ctor();
              thenable.then(function(moduleObject2) {
                if (payload._status === Pending || payload._status === Uninitialized) {
                  var resolved = payload;
                  resolved._status = Resolved;
                  resolved._result = moduleObject2;
                }
              }, function(error2) {
                if (payload._status === Pending || payload._status === Uninitialized) {
                  var rejected = payload;
                  rejected._status = Rejected;
                  rejected._result = error2;
                }
              });
              if (payload._status === Uninitialized) {
                var pending = payload;
                pending._status = Pending;
                pending._result = thenable;
              }
            }
            if (payload._status === Resolved) {
              var moduleObject = payload._result;
              {
                if (moduleObject === void 0) {
                  error("lazy: Expected the result of a dynamic import() call. Instead received: %s\n\nYour code should look like: \n  const MyComponent = lazy(() => import('./MyComponent'))\n\nDid you accidentally put curly braces around the import?", moduleObject);
                }
              }
              {
                if (!("default" in moduleObject)) {
                  error("lazy: Expected the result of a dynamic import() call. Instead received: %s\n\nYour code should look like: \n  const MyComponent = lazy(() => import('./MyComponent'))", moduleObject);
                }
              }
              return moduleObject.default;
            } else {
              throw payload._result;
            }
          }
          function lazy(ctor) {
            var payload = {
              // We use these fields to store the result.
              _status: Uninitialized,
              _result: ctor
            };
            var lazyType = {
              $$typeof: REACT_LAZY_TYPE,
              _payload: payload,
              _init: lazyInitializer
            };
            {
              var defaultProps;
              var propTypes;
              Object.defineProperties(lazyType, {
                defaultProps: {
                  configurable: true,
                  get: function() {
                    return defaultProps;
                  },
                  set: function(newDefaultProps) {
                    error("React.lazy(...): It is not supported to assign `defaultProps` to a lazy component import. Either specify them where the component is defined, or create a wrapping component around it.");
                    defaultProps = newDefaultProps;
                    Object.defineProperty(lazyType, "defaultProps", {
                      enumerable: true
                    });
                  }
                },
                propTypes: {
                  configurable: true,
                  get: function() {
                    return propTypes;
                  },
                  set: function(newPropTypes) {
                    error("React.lazy(...): It is not supported to assign `propTypes` to a lazy component import. Either specify them where the component is defined, or create a wrapping component around it.");
                    propTypes = newPropTypes;
                    Object.defineProperty(lazyType, "propTypes", {
                      enumerable: true
                    });
                  }
                }
              });
            }
            return lazyType;
          }
          function forwardRef(render) {
            {
              if (render != null && render.$$typeof === REACT_MEMO_TYPE) {
                error("forwardRef requires a render function but received a `memo` component. Instead of forwardRef(memo(...)), use memo(forwardRef(...)).");
              } else if (typeof render !== "function") {
                error("forwardRef requires a render function but was given %s.", render === null ? "null" : typeof render);
              } else {
                if (render.length !== 0 && render.length !== 2) {
                  error("forwardRef render functions accept exactly two parameters: props and ref. %s", render.length === 1 ? "Did you forget to use the ref parameter?" : "Any additional parameter will be undefined.");
                }
              }
              if (render != null) {
                if (render.defaultProps != null || render.propTypes != null) {
                  error("forwardRef render functions do not support propTypes or defaultProps. Did you accidentally pass a React component?");
                }
              }
            }
            var elementType = {
              $$typeof: REACT_FORWARD_REF_TYPE,
              render
            };
            {
              var ownName;
              Object.defineProperty(elementType, "displayName", {
                enumerable: false,
                configurable: true,
                get: function() {
                  return ownName;
                },
                set: function(name) {
                  ownName = name;
                  if (!render.name && !render.displayName) {
                    render.displayName = name;
                  }
                }
              });
            }
            return elementType;
          }
          var REACT_MODULE_REFERENCE;
          {
            REACT_MODULE_REFERENCE = Symbol.for("react.module.reference");
          }
          function isValidElementType(type) {
            if (typeof type === "string" || typeof type === "function") {
              return true;
            }
            if (type === REACT_FRAGMENT_TYPE || type === REACT_PROFILER_TYPE || enableDebugTracing || type === REACT_STRICT_MODE_TYPE || type === REACT_SUSPENSE_TYPE || type === REACT_SUSPENSE_LIST_TYPE || enableLegacyHidden || type === REACT_OFFSCREEN_TYPE || enableScopeAPI || enableCacheElement || enableTransitionTracing) {
              return true;
            }
            if (typeof type === "object" && type !== null) {
              if (type.$$typeof === REACT_LAZY_TYPE || type.$$typeof === REACT_MEMO_TYPE || type.$$typeof === REACT_PROVIDER_TYPE || type.$$typeof === REACT_CONTEXT_TYPE || type.$$typeof === REACT_FORWARD_REF_TYPE || // This needs to include all possible module reference object
              // types supported by any Flight configuration anywhere since
              // we don't know which Flight build this will end up being used
              // with.
              type.$$typeof === REACT_MODULE_REFERENCE || type.getModuleId !== void 0) {
                return true;
              }
            }
            return false;
          }
          function memo(type, compare) {
            {
              if (!isValidElementType(type)) {
                error("memo: The first argument must be a component. Instead received: %s", type === null ? "null" : typeof type);
              }
            }
            var elementType = {
              $$typeof: REACT_MEMO_TYPE,
              type,
              compare: compare === void 0 ? null : compare
            };
            {
              var ownName;
              Object.defineProperty(elementType, "displayName", {
                enumerable: false,
                configurable: true,
                get: function() {
                  return ownName;
                },
                set: function(name) {
                  ownName = name;
                  if (!type.name && !type.displayName) {
                    type.displayName = name;
                  }
                }
              });
            }
            return elementType;
          }
          function resolveDispatcher() {
            var dispatcher = ReactCurrentDispatcher.current;
            {
              if (dispatcher === null) {
                error("Invalid hook call. Hooks can only be called inside of the body of a function component. This could happen for one of the following reasons:\n1. You might have mismatching versions of React and the renderer (such as React DOM)\n2. You might be breaking the Rules of Hooks\n3. You might have more than one copy of React in the same app\nSee https://reactjs.org/link/invalid-hook-call for tips about how to debug and fix this problem.");
              }
            }
            return dispatcher;
          }
          function useContext4(Context) {
            var dispatcher = resolveDispatcher();
            {
              if (Context._context !== void 0) {
                var realContext = Context._context;
                if (realContext.Consumer === Context) {
                  error("Calling useContext(Context.Consumer) is not supported, may cause bugs, and will be removed in a future major release. Did you mean to call useContext(Context) instead?");
                } else if (realContext.Provider === Context) {
                  error("Calling useContext(Context.Provider) is not supported. Did you mean to call useContext(Context) instead?");
                }
              }
            }
            return dispatcher.useContext(Context);
          }
          function useState9(initialState) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useState(initialState);
          }
          function useReducer(reducer, initialArg, init) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useReducer(reducer, initialArg, init);
          }
          function useRef3(initialValue) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useRef(initialValue);
          }
          function useEffect7(create, deps) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useEffect(create, deps);
          }
          function useInsertionEffect(create, deps) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useInsertionEffect(create, deps);
          }
          function useLayoutEffect(create, deps) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useLayoutEffect(create, deps);
          }
          function useCallback4(callback, deps) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useCallback(callback, deps);
          }
          function useMemo4(create, deps) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useMemo(create, deps);
          }
          function useImperativeHandle(ref, create, deps) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useImperativeHandle(ref, create, deps);
          }
          function useDebugValue(value, formatterFn) {
            {
              var dispatcher = resolveDispatcher();
              return dispatcher.useDebugValue(value, formatterFn);
            }
          }
          function useTransition() {
            var dispatcher = resolveDispatcher();
            return dispatcher.useTransition();
          }
          function useDeferredValue(value) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useDeferredValue(value);
          }
          function useId() {
            var dispatcher = resolveDispatcher();
            return dispatcher.useId();
          }
          function useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot) {
            var dispatcher = resolveDispatcher();
            return dispatcher.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
          }
          var disabledDepth = 0;
          var prevLog;
          var prevInfo;
          var prevWarn;
          var prevError;
          var prevGroup;
          var prevGroupCollapsed;
          var prevGroupEnd;
          function disabledLog() {
          }
          disabledLog.__reactDisabledLog = true;
          function disableLogs() {
            {
              if (disabledDepth === 0) {
                prevLog = console.log;
                prevInfo = console.info;
                prevWarn = console.warn;
                prevError = console.error;
                prevGroup = console.group;
                prevGroupCollapsed = console.groupCollapsed;
                prevGroupEnd = console.groupEnd;
                var props = {
                  configurable: true,
                  enumerable: true,
                  value: disabledLog,
                  writable: true
                };
                Object.defineProperties(console, {
                  info: props,
                  log: props,
                  warn: props,
                  error: props,
                  group: props,
                  groupCollapsed: props,
                  groupEnd: props
                });
              }
              disabledDepth++;
            }
          }
          function reenableLogs() {
            {
              disabledDepth--;
              if (disabledDepth === 0) {
                var props = {
                  configurable: true,
                  enumerable: true,
                  writable: true
                };
                Object.defineProperties(console, {
                  log: assign({}, props, {
                    value: prevLog
                  }),
                  info: assign({}, props, {
                    value: prevInfo
                  }),
                  warn: assign({}, props, {
                    value: prevWarn
                  }),
                  error: assign({}, props, {
                    value: prevError
                  }),
                  group: assign({}, props, {
                    value: prevGroup
                  }),
                  groupCollapsed: assign({}, props, {
                    value: prevGroupCollapsed
                  }),
                  groupEnd: assign({}, props, {
                    value: prevGroupEnd
                  })
                });
              }
              if (disabledDepth < 0) {
                error("disabledDepth fell below zero. This is a bug in React. Please file an issue.");
              }
            }
          }
          var ReactCurrentDispatcher$1 = ReactSharedInternals.ReactCurrentDispatcher;
          var prefix;
          function describeBuiltInComponentFrame(name, source, ownerFn) {
            {
              if (prefix === void 0) {
                try {
                  throw Error();
                } catch (x) {
                  var match = x.stack.trim().match(/\n( *(at )?)/);
                  prefix = match && match[1] || "";
                }
              }
              return "\n" + prefix + name;
            }
          }
          var reentry = false;
          var componentFrameCache;
          {
            var PossiblyWeakMap = typeof WeakMap === "function" ? WeakMap : Map;
            componentFrameCache = new PossiblyWeakMap();
          }
          function describeNativeComponentFrame(fn, construct) {
            if (!fn || reentry) {
              return "";
            }
            {
              var frame = componentFrameCache.get(fn);
              if (frame !== void 0) {
                return frame;
              }
            }
            var control;
            reentry = true;
            var previousPrepareStackTrace = Error.prepareStackTrace;
            Error.prepareStackTrace = void 0;
            var previousDispatcher;
            {
              previousDispatcher = ReactCurrentDispatcher$1.current;
              ReactCurrentDispatcher$1.current = null;
              disableLogs();
            }
            try {
              if (construct) {
                var Fake = function() {
                  throw Error();
                };
                Object.defineProperty(Fake.prototype, "props", {
                  set: function() {
                    throw Error();
                  }
                });
                if (typeof Reflect === "object" && Reflect.construct) {
                  try {
                    Reflect.construct(Fake, []);
                  } catch (x) {
                    control = x;
                  }
                  Reflect.construct(fn, [], Fake);
                } else {
                  try {
                    Fake.call();
                  } catch (x) {
                    control = x;
                  }
                  fn.call(Fake.prototype);
                }
              } else {
                try {
                  throw Error();
                } catch (x) {
                  control = x;
                }
                fn();
              }
            } catch (sample) {
              if (sample && control && typeof sample.stack === "string") {
                var sampleLines = sample.stack.split("\n");
                var controlLines = control.stack.split("\n");
                var s = sampleLines.length - 1;
                var c = controlLines.length - 1;
                while (s >= 1 && c >= 0 && sampleLines[s] !== controlLines[c]) {
                  c--;
                }
                for (; s >= 1 && c >= 0; s--, c--) {
                  if (sampleLines[s] !== controlLines[c]) {
                    if (s !== 1 || c !== 1) {
                      do {
                        s--;
                        c--;
                        if (c < 0 || sampleLines[s] !== controlLines[c]) {
                          var _frame = "\n" + sampleLines[s].replace(" at new ", " at ");
                          if (fn.displayName && _frame.includes("<anonymous>")) {
                            _frame = _frame.replace("<anonymous>", fn.displayName);
                          }
                          {
                            if (typeof fn === "function") {
                              componentFrameCache.set(fn, _frame);
                            }
                          }
                          return _frame;
                        }
                      } while (s >= 1 && c >= 0);
                    }
                    break;
                  }
                }
              }
            } finally {
              reentry = false;
              {
                ReactCurrentDispatcher$1.current = previousDispatcher;
                reenableLogs();
              }
              Error.prepareStackTrace = previousPrepareStackTrace;
            }
            var name = fn ? fn.displayName || fn.name : "";
            var syntheticFrame = name ? describeBuiltInComponentFrame(name) : "";
            {
              if (typeof fn === "function") {
                componentFrameCache.set(fn, syntheticFrame);
              }
            }
            return syntheticFrame;
          }
          function describeFunctionComponentFrame(fn, source, ownerFn) {
            {
              return describeNativeComponentFrame(fn, false);
            }
          }
          function shouldConstruct(Component2) {
            var prototype = Component2.prototype;
            return !!(prototype && prototype.isReactComponent);
          }
          function describeUnknownElementTypeFrameInDEV(type, source, ownerFn) {
            if (type == null) {
              return "";
            }
            if (typeof type === "function") {
              {
                return describeNativeComponentFrame(type, shouldConstruct(type));
              }
            }
            if (typeof type === "string") {
              return describeBuiltInComponentFrame(type);
            }
            switch (type) {
              case REACT_SUSPENSE_TYPE:
                return describeBuiltInComponentFrame("Suspense");
              case REACT_SUSPENSE_LIST_TYPE:
                return describeBuiltInComponentFrame("SuspenseList");
            }
            if (typeof type === "object") {
              switch (type.$$typeof) {
                case REACT_FORWARD_REF_TYPE:
                  return describeFunctionComponentFrame(type.render);
                case REACT_MEMO_TYPE:
                  return describeUnknownElementTypeFrameInDEV(type.type, source, ownerFn);
                case REACT_LAZY_TYPE: {
                  var lazyComponent = type;
                  var payload = lazyComponent._payload;
                  var init = lazyComponent._init;
                  try {
                    return describeUnknownElementTypeFrameInDEV(init(payload), source, ownerFn);
                  } catch (x) {
                  }
                }
              }
            }
            return "";
          }
          var loggedTypeFailures = {};
          var ReactDebugCurrentFrame$1 = ReactSharedInternals.ReactDebugCurrentFrame;
          function setCurrentlyValidatingElement(element) {
            {
              if (element) {
                var owner = element._owner;
                var stack = describeUnknownElementTypeFrameInDEV(element.type, element._source, owner ? owner.type : null);
                ReactDebugCurrentFrame$1.setExtraStackFrame(stack);
              } else {
                ReactDebugCurrentFrame$1.setExtraStackFrame(null);
              }
            }
          }
          function checkPropTypes(typeSpecs, values, location, componentName, element) {
            {
              var has = Function.call.bind(hasOwnProperty);
              for (var typeSpecName in typeSpecs) {
                if (has(typeSpecs, typeSpecName)) {
                  var error$1 = void 0;
                  try {
                    if (typeof typeSpecs[typeSpecName] !== "function") {
                      var err = Error((componentName || "React class") + ": " + location + " type `" + typeSpecName + "` is invalid; it must be a function, usually from the `prop-types` package, but received `" + typeof typeSpecs[typeSpecName] + "`.This often happens because of typos such as `PropTypes.function` instead of `PropTypes.func`.");
                      err.name = "Invariant Violation";
                      throw err;
                    }
                    error$1 = typeSpecs[typeSpecName](values, typeSpecName, componentName, location, null, "SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED");
                  } catch (ex) {
                    error$1 = ex;
                  }
                  if (error$1 && !(error$1 instanceof Error)) {
                    setCurrentlyValidatingElement(element);
                    error("%s: type specification of %s `%s` is invalid; the type checker function must return `null` or an `Error` but returned a %s. You may have forgotten to pass an argument to the type checker creator (arrayOf, instanceOf, objectOf, oneOf, oneOfType, and shape all require an argument).", componentName || "React class", location, typeSpecName, typeof error$1);
                    setCurrentlyValidatingElement(null);
                  }
                  if (error$1 instanceof Error && !(error$1.message in loggedTypeFailures)) {
                    loggedTypeFailures[error$1.message] = true;
                    setCurrentlyValidatingElement(element);
                    error("Failed %s type: %s", location, error$1.message);
                    setCurrentlyValidatingElement(null);
                  }
                }
              }
            }
          }
          function setCurrentlyValidatingElement$1(element) {
            {
              if (element) {
                var owner = element._owner;
                var stack = describeUnknownElementTypeFrameInDEV(element.type, element._source, owner ? owner.type : null);
                setExtraStackFrame(stack);
              } else {
                setExtraStackFrame(null);
              }
            }
          }
          var propTypesMisspellWarningShown;
          {
            propTypesMisspellWarningShown = false;
          }
          function getDeclarationErrorAddendum() {
            if (ReactCurrentOwner.current) {
              var name = getComponentNameFromType(ReactCurrentOwner.current.type);
              if (name) {
                return "\n\nCheck the render method of `" + name + "`.";
              }
            }
            return "";
          }
          function getSourceInfoErrorAddendum(source) {
            if (source !== void 0) {
              var fileName = source.fileName.replace(/^.*[\\\/]/, "");
              var lineNumber = source.lineNumber;
              return "\n\nCheck your code at " + fileName + ":" + lineNumber + ".";
            }
            return "";
          }
          function getSourceInfoErrorAddendumForProps(elementProps) {
            if (elementProps !== null && elementProps !== void 0) {
              return getSourceInfoErrorAddendum(elementProps.__source);
            }
            return "";
          }
          var ownerHasKeyUseWarning = {};
          function getCurrentComponentErrorInfo(parentType) {
            var info = getDeclarationErrorAddendum();
            if (!info) {
              var parentName = typeof parentType === "string" ? parentType : parentType.displayName || parentType.name;
              if (parentName) {
                info = "\n\nCheck the top-level render call using <" + parentName + ">.";
              }
            }
            return info;
          }
          function validateExplicitKey(element, parentType) {
            if (!element._store || element._store.validated || element.key != null) {
              return;
            }
            element._store.validated = true;
            var currentComponentErrorInfo = getCurrentComponentErrorInfo(parentType);
            if (ownerHasKeyUseWarning[currentComponentErrorInfo]) {
              return;
            }
            ownerHasKeyUseWarning[currentComponentErrorInfo] = true;
            var childOwner = "";
            if (element && element._owner && element._owner !== ReactCurrentOwner.current) {
              childOwner = " It was passed a child from " + getComponentNameFromType(element._owner.type) + ".";
            }
            {
              setCurrentlyValidatingElement$1(element);
              error('Each child in a list should have a unique "key" prop.%s%s See https://reactjs.org/link/warning-keys for more information.', currentComponentErrorInfo, childOwner);
              setCurrentlyValidatingElement$1(null);
            }
          }
          function validateChildKeys(node, parentType) {
            if (typeof node !== "object") {
              return;
            }
            if (isArray(node)) {
              for (var i = 0; i < node.length; i++) {
                var child = node[i];
                if (isValidElement(child)) {
                  validateExplicitKey(child, parentType);
                }
              }
            } else if (isValidElement(node)) {
              if (node._store) {
                node._store.validated = true;
              }
            } else if (node) {
              var iteratorFn = getIteratorFn(node);
              if (typeof iteratorFn === "function") {
                if (iteratorFn !== node.entries) {
                  var iterator = iteratorFn.call(node);
                  var step;
                  while (!(step = iterator.next()).done) {
                    if (isValidElement(step.value)) {
                      validateExplicitKey(step.value, parentType);
                    }
                  }
                }
              }
            }
          }
          function validatePropTypes(element) {
            {
              var type = element.type;
              if (type === null || type === void 0 || typeof type === "string") {
                return;
              }
              var propTypes;
              if (typeof type === "function") {
                propTypes = type.propTypes;
              } else if (typeof type === "object" && (type.$$typeof === REACT_FORWARD_REF_TYPE || // Note: Memo only checks outer props here.
              // Inner props are checked in the reconciler.
              type.$$typeof === REACT_MEMO_TYPE)) {
                propTypes = type.propTypes;
              } else {
                return;
              }
              if (propTypes) {
                var name = getComponentNameFromType(type);
                checkPropTypes(propTypes, element.props, "prop", name, element);
              } else if (type.PropTypes !== void 0 && !propTypesMisspellWarningShown) {
                propTypesMisspellWarningShown = true;
                var _name = getComponentNameFromType(type);
                error("Component %s declared `PropTypes` instead of `propTypes`. Did you misspell the property assignment?", _name || "Unknown");
              }
              if (typeof type.getDefaultProps === "function" && !type.getDefaultProps.isReactClassApproved) {
                error("getDefaultProps is only used on classic React.createClass definitions. Use a static property named `defaultProps` instead.");
              }
            }
          }
          function validateFragmentProps(fragment) {
            {
              var keys = Object.keys(fragment.props);
              for (var i = 0; i < keys.length; i++) {
                var key = keys[i];
                if (key !== "children" && key !== "key") {
                  setCurrentlyValidatingElement$1(fragment);
                  error("Invalid prop `%s` supplied to `React.Fragment`. React.Fragment can only have `key` and `children` props.", key);
                  setCurrentlyValidatingElement$1(null);
                  break;
                }
              }
              if (fragment.ref !== null) {
                setCurrentlyValidatingElement$1(fragment);
                error("Invalid attribute `ref` supplied to `React.Fragment`.");
                setCurrentlyValidatingElement$1(null);
              }
            }
          }
          function createElementWithValidation(type, props, children) {
            var validType = isValidElementType(type);
            if (!validType) {
              var info = "";
              if (type === void 0 || typeof type === "object" && type !== null && Object.keys(type).length === 0) {
                info += " You likely forgot to export your component from the file it's defined in, or you might have mixed up default and named imports.";
              }
              var sourceInfo = getSourceInfoErrorAddendumForProps(props);
              if (sourceInfo) {
                info += sourceInfo;
              } else {
                info += getDeclarationErrorAddendum();
              }
              var typeString;
              if (type === null) {
                typeString = "null";
              } else if (isArray(type)) {
                typeString = "array";
              } else if (type !== void 0 && type.$$typeof === REACT_ELEMENT_TYPE) {
                typeString = "<" + (getComponentNameFromType(type.type) || "Unknown") + " />";
                info = " Did you accidentally export a JSX literal instead of a component?";
              } else {
                typeString = typeof type;
              }
              {
                error("React.createElement: type is invalid -- expected a string (for built-in components) or a class/function (for composite components) but got: %s.%s", typeString, info);
              }
            }
            var element = createElement.apply(this, arguments);
            if (element == null) {
              return element;
            }
            if (validType) {
              for (var i = 2; i < arguments.length; i++) {
                validateChildKeys(arguments[i], type);
              }
            }
            if (type === REACT_FRAGMENT_TYPE) {
              validateFragmentProps(element);
            } else {
              validatePropTypes(element);
            }
            return element;
          }
          var didWarnAboutDeprecatedCreateFactory = false;
          function createFactoryWithValidation(type) {
            var validatedFactory = createElementWithValidation.bind(null, type);
            validatedFactory.type = type;
            {
              if (!didWarnAboutDeprecatedCreateFactory) {
                didWarnAboutDeprecatedCreateFactory = true;
                warn("React.createFactory() is deprecated and will be removed in a future major release. Consider using JSX or use React.createElement() directly instead.");
              }
              Object.defineProperty(validatedFactory, "type", {
                enumerable: false,
                get: function() {
                  warn("Factory.type is deprecated. Access the class directly before passing it to createFactory.");
                  Object.defineProperty(this, "type", {
                    value: type
                  });
                  return type;
                }
              });
            }
            return validatedFactory;
          }
          function cloneElementWithValidation(element, props, children) {
            var newElement = cloneElement.apply(this, arguments);
            for (var i = 2; i < arguments.length; i++) {
              validateChildKeys(arguments[i], newElement.type);
            }
            validatePropTypes(newElement);
            return newElement;
          }
          function startTransition(scope, options) {
            var prevTransition = ReactCurrentBatchConfig.transition;
            ReactCurrentBatchConfig.transition = {};
            var currentTransition = ReactCurrentBatchConfig.transition;
            {
              ReactCurrentBatchConfig.transition._updatedFibers = /* @__PURE__ */ new Set();
            }
            try {
              scope();
            } finally {
              ReactCurrentBatchConfig.transition = prevTransition;
              {
                if (prevTransition === null && currentTransition._updatedFibers) {
                  var updatedFibersCount = currentTransition._updatedFibers.size;
                  if (updatedFibersCount > 10) {
                    warn("Detected a large number of updates inside startTransition. If this is due to a subscription please re-write it to use React provided hooks. Otherwise concurrent mode guarantees are off the table.");
                  }
                  currentTransition._updatedFibers.clear();
                }
              }
            }
          }
          var didWarnAboutMessageChannel = false;
          var enqueueTaskImpl = null;
          function enqueueTask(task) {
            if (enqueueTaskImpl === null) {
              try {
                var requireString = ("require" + Math.random()).slice(0, 7);
                var nodeRequire = module && module[requireString];
                enqueueTaskImpl = nodeRequire.call(module, "timers").setImmediate;
              } catch (_err) {
                enqueueTaskImpl = function(callback) {
                  {
                    if (didWarnAboutMessageChannel === false) {
                      didWarnAboutMessageChannel = true;
                      if (typeof MessageChannel === "undefined") {
                        error("This browser does not have a MessageChannel implementation, so enqueuing tasks via await act(async () => ...) will fail. Please file an issue at https://github.com/facebook/react/issues if you encounter this warning.");
                      }
                    }
                  }
                  var channel = new MessageChannel();
                  channel.port1.onmessage = callback;
                  channel.port2.postMessage(void 0);
                };
              }
            }
            return enqueueTaskImpl(task);
          }
          var actScopeDepth = 0;
          var didWarnNoAwaitAct = false;
          function act(callback) {
            {
              var prevActScopeDepth = actScopeDepth;
              actScopeDepth++;
              if (ReactCurrentActQueue.current === null) {
                ReactCurrentActQueue.current = [];
              }
              var prevIsBatchingLegacy = ReactCurrentActQueue.isBatchingLegacy;
              var result;
              try {
                ReactCurrentActQueue.isBatchingLegacy = true;
                result = callback();
                if (!prevIsBatchingLegacy && ReactCurrentActQueue.didScheduleLegacyUpdate) {
                  var queue = ReactCurrentActQueue.current;
                  if (queue !== null) {
                    ReactCurrentActQueue.didScheduleLegacyUpdate = false;
                    flushActQueue(queue);
                  }
                }
              } catch (error2) {
                popActScope(prevActScopeDepth);
                throw error2;
              } finally {
                ReactCurrentActQueue.isBatchingLegacy = prevIsBatchingLegacy;
              }
              if (result !== null && typeof result === "object" && typeof result.then === "function") {
                var thenableResult = result;
                var wasAwaited = false;
                var thenable = {
                  then: function(resolve, reject) {
                    wasAwaited = true;
                    thenableResult.then(function(returnValue2) {
                      popActScope(prevActScopeDepth);
                      if (actScopeDepth === 0) {
                        recursivelyFlushAsyncActWork(returnValue2, resolve, reject);
                      } else {
                        resolve(returnValue2);
                      }
                    }, function(error2) {
                      popActScope(prevActScopeDepth);
                      reject(error2);
                    });
                  }
                };
                {
                  if (!didWarnNoAwaitAct && typeof Promise !== "undefined") {
                    Promise.resolve().then(function() {
                    }).then(function() {
                      if (!wasAwaited) {
                        didWarnNoAwaitAct = true;
                        error("You called act(async () => ...) without await. This could lead to unexpected testing behaviour, interleaving multiple act calls and mixing their scopes. You should - await act(async () => ...);");
                      }
                    });
                  }
                }
                return thenable;
              } else {
                var returnValue = result;
                popActScope(prevActScopeDepth);
                if (actScopeDepth === 0) {
                  var _queue = ReactCurrentActQueue.current;
                  if (_queue !== null) {
                    flushActQueue(_queue);
                    ReactCurrentActQueue.current = null;
                  }
                  var _thenable = {
                    then: function(resolve, reject) {
                      if (ReactCurrentActQueue.current === null) {
                        ReactCurrentActQueue.current = [];
                        recursivelyFlushAsyncActWork(returnValue, resolve, reject);
                      } else {
                        resolve(returnValue);
                      }
                    }
                  };
                  return _thenable;
                } else {
                  var _thenable2 = {
                    then: function(resolve, reject) {
                      resolve(returnValue);
                    }
                  };
                  return _thenable2;
                }
              }
            }
          }
          function popActScope(prevActScopeDepth) {
            {
              if (prevActScopeDepth !== actScopeDepth - 1) {
                error("You seem to have overlapping act() calls, this is not supported. Be sure to await previous act() calls before making a new one. ");
              }
              actScopeDepth = prevActScopeDepth;
            }
          }
          function recursivelyFlushAsyncActWork(returnValue, resolve, reject) {
            {
              var queue = ReactCurrentActQueue.current;
              if (queue !== null) {
                try {
                  flushActQueue(queue);
                  enqueueTask(function() {
                    if (queue.length === 0) {
                      ReactCurrentActQueue.current = null;
                      resolve(returnValue);
                    } else {
                      recursivelyFlushAsyncActWork(returnValue, resolve, reject);
                    }
                  });
                } catch (error2) {
                  reject(error2);
                }
              } else {
                resolve(returnValue);
              }
            }
          }
          var isFlushing = false;
          function flushActQueue(queue) {
            {
              if (!isFlushing) {
                isFlushing = true;
                var i = 0;
                try {
                  for (; i < queue.length; i++) {
                    var callback = queue[i];
                    do {
                      callback = callback(true);
                    } while (callback !== null);
                  }
                  queue.length = 0;
                } catch (error2) {
                  queue = queue.slice(i + 1);
                  throw error2;
                } finally {
                  isFlushing = false;
                }
              }
            }
          }
          var createElement$1 = createElementWithValidation;
          var cloneElement$1 = cloneElementWithValidation;
          var createFactory = createFactoryWithValidation;
          var Children = {
            map: mapChildren,
            forEach: forEachChildren,
            count: countChildren,
            toArray,
            only: onlyChild
          };
          exports.Children = Children;
          exports.Component = Component;
          exports.Fragment = REACT_FRAGMENT_TYPE;
          exports.Profiler = REACT_PROFILER_TYPE;
          exports.PureComponent = PureComponent;
          exports.StrictMode = REACT_STRICT_MODE_TYPE;
          exports.Suspense = REACT_SUSPENSE_TYPE;
          exports.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = ReactSharedInternals;
          exports.act = act;
          exports.cloneElement = cloneElement$1;
          exports.createContext = createContext4;
          exports.createElement = createElement$1;
          exports.createFactory = createFactory;
          exports.createRef = createRef;
          exports.forwardRef = forwardRef;
          exports.isValidElement = isValidElement;
          exports.lazy = lazy;
          exports.memo = memo;
          exports.startTransition = startTransition;
          exports.unstable_act = act;
          exports.useCallback = useCallback4;
          exports.useContext = useContext4;
          exports.useDebugValue = useDebugValue;
          exports.useDeferredValue = useDeferredValue;
          exports.useEffect = useEffect7;
          exports.useId = useId;
          exports.useImperativeHandle = useImperativeHandle;
          exports.useInsertionEffect = useInsertionEffect;
          exports.useLayoutEffect = useLayoutEffect;
          exports.useMemo = useMemo4;
          exports.useReducer = useReducer;
          exports.useRef = useRef3;
          exports.useState = useState9;
          exports.useSyncExternalStore = useSyncExternalStore;
          exports.useTransition = useTransition;
          exports.version = ReactVersion;
          if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ !== "undefined" && typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStop === "function") {
            __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStop(new Error());
          }
        })();
      }
    }
  });

  // node_modules/react/index.js
  var require_react = __commonJS({
    "node_modules/react/index.js"(exports, module) {
      "use strict";
      if (false) {
        module.exports = null;
      } else {
        module.exports = require_react_development();
      }
    }
  });

  // node_modules/sweetalert2/dist/sweetalert2.all.js
  var require_sweetalert2_all = __commonJS({
    "node_modules/sweetalert2/dist/sweetalert2.all.js"(exports, module) {
      (function(global, factory) {
        typeof exports === "object" && typeof module !== "undefined" ? module.exports = factory() : typeof define === "function" && define.amd ? define(factory) : (global = typeof globalThis !== "undefined" ? globalThis : global || self, global.Sweetalert2 = factory());
      })(exports, function() {
        "use strict";
        function _assertClassBrand(e, t, n) {
          if ("function" == typeof e ? e === t : e.has(t)) return arguments.length < 3 ? t : n;
          throw new TypeError("Private element is not present on this object");
        }
        function _checkPrivateRedeclaration(e, t) {
          if (t.has(e)) throw new TypeError("Cannot initialize the same private elements twice on an object");
        }
        function _classPrivateFieldGet2(s, a) {
          return s.get(_assertClassBrand(s, a));
        }
        function _classPrivateFieldInitSpec(e, t, a) {
          _checkPrivateRedeclaration(e, t), t.set(e, a);
        }
        function _classPrivateFieldSet2(s, a, r) {
          return s.set(_assertClassBrand(s, a), r), r;
        }
        const RESTORE_FOCUS_TIMEOUT = 100;
        const globalState = {};
        const focusPreviousActiveElement = () => {
          if (globalState.previousActiveElement instanceof HTMLElement) {
            globalState.previousActiveElement.focus();
            globalState.previousActiveElement = null;
          } else if (document.body) {
            document.body.focus();
          }
        };
        const restoreActiveElement = (returnFocus) => {
          return new Promise((resolve) => {
            if (!returnFocus) {
              return resolve();
            }
            const x = window.scrollX;
            const y = window.scrollY;
            globalState.restoreFocusTimeout = setTimeout(() => {
              focusPreviousActiveElement();
              resolve();
            }, RESTORE_FOCUS_TIMEOUT);
            window.scrollTo(x, y);
          });
        };
        const swalPrefix = "swal2-";
        const classNames = ["container", "shown", "height-auto", "iosfix", "popup", "modal", "no-backdrop", "no-transition", "toast", "toast-shown", "show", "hide", "close", "title", "html-container", "actions", "confirm", "deny", "cancel", "footer", "icon", "icon-content", "image", "input", "file", "range", "select", "radio", "checkbox", "label", "textarea", "inputerror", "input-label", "validation-message", "progress-steps", "active-progress-step", "progress-step", "progress-step-line", "loader", "loading", "styled", "top", "top-start", "top-end", "top-left", "top-right", "center", "center-start", "center-end", "center-left", "center-right", "bottom", "bottom-start", "bottom-end", "bottom-left", "bottom-right", "grow-row", "grow-column", "grow-fullscreen", "rtl", "timer-progress-bar", "timer-progress-bar-container", "scrollbar-measure", "icon-success", "icon-warning", "icon-info", "icon-question", "icon-error", "draggable", "dragging"];
        const swalClasses = classNames.reduce(
          (acc, className) => {
            acc[className] = swalPrefix + className;
            return acc;
          },
          /** @type {SwalClasses} */
          {}
        );
        const icons = ["success", "warning", "info", "question", "error"];
        const iconTypes = icons.reduce(
          (acc, icon) => {
            acc[icon] = swalPrefix + icon;
            return acc;
          },
          /** @type {SwalIcons} */
          {}
        );
        const consolePrefix = "SweetAlert2:";
        const capitalizeFirstLetter = (str) => str.charAt(0).toUpperCase() + str.slice(1);
        const warn = (message) => {
          console.warn(`${consolePrefix} ${typeof message === "object" ? message.join(" ") : message}`);
        };
        const error = (message) => {
          console.error(`${consolePrefix} ${message}`);
        };
        const previousWarnOnceMessages = [];
        const warnOnce = (message) => {
          if (!previousWarnOnceMessages.includes(message)) {
            previousWarnOnceMessages.push(message);
            warn(message);
          }
        };
        const warnAboutDeprecation = (deprecatedParam, useInstead = null) => {
          warnOnce(`"${deprecatedParam}" is deprecated and will be removed in the next major release.${useInstead ? ` Use "${useInstead}" instead.` : ""}`);
        };
        const callIfFunction = (arg) => typeof arg === "function" ? arg() : arg;
        const hasToPromiseFn = (arg) => arg && typeof arg.toPromise === "function";
        const asPromise = (arg) => hasToPromiseFn(arg) ? arg.toPromise() : Promise.resolve(arg);
        const isPromise = (arg) => arg && Promise.resolve(arg) === arg;
        const getContainer = () => document.body.querySelector(`.${swalClasses.container}`);
        const elementBySelector = (selectorString) => {
          const container = getContainer();
          return container ? container.querySelector(selectorString) : null;
        };
        const elementByClass = (className) => {
          return elementBySelector(`.${className}`);
        };
        const getPopup = () => elementByClass(swalClasses.popup);
        const getIcon = () => elementByClass(swalClasses.icon);
        const getIconContent = () => elementByClass(swalClasses["icon-content"]);
        const getTitle = () => elementByClass(swalClasses.title);
        const getHtmlContainer = () => elementByClass(swalClasses["html-container"]);
        const getImage = () => elementByClass(swalClasses.image);
        const getProgressSteps = () => elementByClass(swalClasses["progress-steps"]);
        const getValidationMessage = () => elementByClass(swalClasses["validation-message"]);
        const getConfirmButton = () => (
          /** @type {HTMLButtonElement} */
          elementBySelector(`.${swalClasses.actions} .${swalClasses.confirm}`)
        );
        const getCancelButton = () => (
          /** @type {HTMLButtonElement} */
          elementBySelector(`.${swalClasses.actions} .${swalClasses.cancel}`)
        );
        const getDenyButton = () => (
          /** @type {HTMLButtonElement} */
          elementBySelector(`.${swalClasses.actions} .${swalClasses.deny}`)
        );
        const getInputLabel = () => elementByClass(swalClasses["input-label"]);
        const getLoader = () => elementBySelector(`.${swalClasses.loader}`);
        const getActions = () => elementByClass(swalClasses.actions);
        const getFooter = () => elementByClass(swalClasses.footer);
        const getTimerProgressBar = () => elementByClass(swalClasses["timer-progress-bar"]);
        const getCloseButton = () => elementByClass(swalClasses.close);
        const focusable = `
  a[href],
  area[href],
  input:not([disabled]),
  select:not([disabled]),
  textarea:not([disabled]),
  button:not([disabled]),
  iframe,
  object,
  embed,
  [tabindex="0"],
  [contenteditable],
  audio[controls],
  video[controls],
  summary
`;
        const getFocusableElements = () => {
          const popup = getPopup();
          if (!popup) {
            return [];
          }
          const focusableElementsWithTabindex = popup.querySelectorAll('[tabindex]:not([tabindex="-1"]):not([tabindex="0"])');
          const focusableElementsWithTabindexSorted = Array.from(focusableElementsWithTabindex).sort((a, b) => {
            const tabindexA = parseInt(a.getAttribute("tabindex") || "0");
            const tabindexB = parseInt(b.getAttribute("tabindex") || "0");
            if (tabindexA > tabindexB) {
              return 1;
            } else if (tabindexA < tabindexB) {
              return -1;
            }
            return 0;
          });
          const otherFocusableElements = popup.querySelectorAll(focusable);
          const otherFocusableElementsFiltered = Array.from(otherFocusableElements).filter((el) => el.getAttribute("tabindex") !== "-1");
          return [...new Set(focusableElementsWithTabindexSorted.concat(otherFocusableElementsFiltered))].filter((el) => isVisible$1(el));
        };
        const isModal = () => {
          return hasClass(document.body, swalClasses.shown) && !hasClass(document.body, swalClasses["toast-shown"]) && !hasClass(document.body, swalClasses["no-backdrop"]);
        };
        const isToast = () => {
          const popup = getPopup();
          if (!popup) {
            return false;
          }
          return hasClass(popup, swalClasses.toast);
        };
        const isLoading = () => {
          const popup = getPopup();
          if (!popup) {
            return false;
          }
          return popup.hasAttribute("data-loading");
        };
        const setInnerHtml = (elem, html) => {
          elem.textContent = "";
          if (html) {
            const parser = new DOMParser();
            const parsed = parser.parseFromString(html, `text/html`);
            const head = parsed.querySelector("head");
            if (head) {
              Array.from(head.childNodes).forEach((child) => {
                elem.appendChild(child);
              });
            }
            const body = parsed.querySelector("body");
            if (body) {
              Array.from(body.childNodes).forEach((child) => {
                if (child instanceof HTMLVideoElement || child instanceof HTMLAudioElement) {
                  elem.appendChild(child.cloneNode(true));
                } else {
                  elem.appendChild(child);
                }
              });
            }
          }
        };
        const hasClass = (elem, className) => {
          if (!className) {
            return false;
          }
          const classList = className.split(/\s+/);
          for (let i = 0; i < classList.length; i++) {
            if (!elem.classList.contains(classList[i])) {
              return false;
            }
          }
          return true;
        };
        const removeCustomClasses = (elem, params) => {
          Array.from(elem.classList).forEach((className) => {
            if (!Object.values(swalClasses).includes(className) && !Object.values(iconTypes).includes(className) && !Object.values(params.showClass || {}).includes(className)) {
              elem.classList.remove(className);
            }
          });
        };
        const applyCustomClass = (elem, params, className) => {
          removeCustomClasses(elem, params);
          if (!params.customClass) {
            return;
          }
          const customClass = params.customClass[
            /** @type {keyof SweetAlertCustomClass} */
            className
          ];
          if (!customClass) {
            return;
          }
          if (typeof customClass !== "string" && !customClass.forEach) {
            warn(`Invalid type of customClass.${className}! Expected string or iterable object, got "${typeof customClass}"`);
            return;
          }
          addClass(elem, customClass);
        };
        const getInput$1 = (popup, inputClass) => {
          if (!inputClass) {
            return null;
          }
          switch (inputClass) {
            case "select":
            case "textarea":
            case "file":
              return popup.querySelector(`.${swalClasses.popup} > .${swalClasses[inputClass]}`);
            case "checkbox":
              return popup.querySelector(`.${swalClasses.popup} > .${swalClasses.checkbox} input`);
            case "radio":
              return popup.querySelector(`.${swalClasses.popup} > .${swalClasses.radio} input:checked`) || popup.querySelector(`.${swalClasses.popup} > .${swalClasses.radio} input:first-child`);
            case "range":
              return popup.querySelector(`.${swalClasses.popup} > .${swalClasses.range} input`);
            default:
              return popup.querySelector(`.${swalClasses.popup} > .${swalClasses.input}`);
          }
        };
        const focusInput = (input) => {
          input.focus();
          if (input.type !== "file") {
            const val = input.value;
            input.value = "";
            input.value = val;
          }
        };
        const toggleClass = (target, classList, condition) => {
          if (!target || !classList) {
            return;
          }
          if (typeof classList === "string") {
            classList = classList.split(/\s+/).filter(Boolean);
          }
          classList.forEach((className) => {
            if (Array.isArray(target)) {
              target.forEach((elem) => {
                if (condition) {
                  elem.classList.add(className);
                } else {
                  elem.classList.remove(className);
                }
              });
            } else {
              if (condition) {
                target.classList.add(className);
              } else {
                target.classList.remove(className);
              }
            }
          });
        };
        const addClass = (target, classList) => {
          toggleClass(target, classList, true);
        };
        const removeClass = (target, classList) => {
          toggleClass(target, classList, false);
        };
        const getDirectChildByClass = (elem, className) => {
          const children = Array.from(elem.children);
          for (let i = 0; i < children.length; i++) {
            const child = children[i];
            if (child instanceof HTMLElement && hasClass(child, className)) {
              return child;
            }
          }
        };
        const applyNumericalStyle = (elem, property, value) => {
          if (value === `${parseInt(`${value}`)}`) {
            value = parseInt(value);
          }
          if (value || parseInt(`${value}`) === 0) {
            elem.style.setProperty(property, typeof value === "number" ? `${value}px` : (
              /** @type {string} */
              value
            ));
          } else {
            elem.style.removeProperty(property);
          }
        };
        const show = (elem, display = "flex") => {
          if (!elem) {
            return;
          }
          elem.style.display = display;
        };
        const hide = (elem) => {
          if (!elem) {
            return;
          }
          elem.style.display = "none";
        };
        const showWhenInnerHtmlPresent = (elem, display = "block") => {
          if (!elem) {
            return;
          }
          new MutationObserver(() => {
            toggle(elem, elem.innerHTML, display);
          }).observe(elem, {
            childList: true,
            subtree: true
          });
        };
        const setStyle = (parent, selector, property, value) => {
          const el = parent.querySelector(selector);
          if (el) {
            el.style.setProperty(property, value);
          }
        };
        const toggle = (elem, condition, display = "flex") => {
          if (condition) {
            show(elem, display);
          } else {
            hide(elem);
          }
        };
        const isVisible$1 = (elem) => Boolean(elem && (elem.offsetWidth || elem.offsetHeight || elem.getClientRects().length));
        const allButtonsAreHidden = () => !isVisible$1(getConfirmButton()) && !isVisible$1(getDenyButton()) && !isVisible$1(getCancelButton());
        const isScrollable = (elem) => Boolean(elem.scrollHeight > elem.clientHeight);
        const selfOrParentIsScrollable = (element, stopElement) => {
          let parent = (
            /** @type {HTMLElement | null} */
            element
          );
          while (parent && parent !== stopElement) {
            if (isScrollable(parent)) {
              return true;
            }
            parent = parent.parentElement;
          }
          return false;
        };
        const hasCssAnimation = (elem) => {
          const style = window.getComputedStyle(elem);
          const animDuration = parseFloat(style.getPropertyValue("animation-duration") || "0");
          const transDuration = parseFloat(style.getPropertyValue("transition-duration") || "0");
          return animDuration > 0 || transDuration > 0;
        };
        const animateTimerProgressBar = (timer, reset = false) => {
          const timerProgressBar = getTimerProgressBar();
          if (!timerProgressBar) {
            return;
          }
          if (isVisible$1(timerProgressBar)) {
            if (reset) {
              timerProgressBar.style.transition = "none";
              timerProgressBar.style.width = "100%";
            }
            setTimeout(() => {
              timerProgressBar.style.transition = `width ${timer / 1e3}s linear`;
              timerProgressBar.style.width = "0%";
            }, 10);
          }
        };
        const stopTimerProgressBar = () => {
          const timerProgressBar = getTimerProgressBar();
          if (!timerProgressBar) {
            return;
          }
          const timerProgressBarWidth = parseInt(window.getComputedStyle(timerProgressBar).width);
          timerProgressBar.style.removeProperty("transition");
          timerProgressBar.style.width = "100%";
          const timerProgressBarFullWidth = parseInt(window.getComputedStyle(timerProgressBar).width);
          const timerProgressBarPercent = timerProgressBarWidth / timerProgressBarFullWidth * 100;
          timerProgressBar.style.width = `${timerProgressBarPercent}%`;
        };
        const isNodeEnv = () => typeof window === "undefined" || typeof document === "undefined";
        const sweetHTML = `
 <div aria-labelledby="${swalClasses.title}" aria-describedby="${swalClasses["html-container"]}" class="${swalClasses.popup}" tabindex="-1">
   <button type="button" class="${swalClasses.close}"></button>
   <ul class="${swalClasses["progress-steps"]}"></ul>
   <div class="${swalClasses.icon}"></div>
   <img class="${swalClasses.image}" />
   <h2 class="${swalClasses.title}" id="${swalClasses.title}"></h2>
   <div class="${swalClasses["html-container"]}" id="${swalClasses["html-container"]}"></div>
   <input class="${swalClasses.input}" id="${swalClasses.input}" />
   <input type="file" class="${swalClasses.file}" />
   <div class="${swalClasses.range}">
     <input type="range" />
     <output></output>
   </div>
   <select class="${swalClasses.select}" id="${swalClasses.select}"></select>
   <div class="${swalClasses.radio}"></div>
   <label class="${swalClasses.checkbox}">
     <input type="checkbox" id="${swalClasses.checkbox}" />
     <span class="${swalClasses.label}"></span>
   </label>
   <textarea class="${swalClasses.textarea}" id="${swalClasses.textarea}"></textarea>
   <div class="${swalClasses["validation-message"]}" id="${swalClasses["validation-message"]}"></div>
   <div class="${swalClasses.actions}">
     <div class="${swalClasses.loader}"></div>
     <button type="button" class="${swalClasses.confirm}"></button>
     <button type="button" class="${swalClasses.deny}"></button>
     <button type="button" class="${swalClasses.cancel}"></button>
   </div>
   <div class="${swalClasses.footer}"></div>
   <div class="${swalClasses["timer-progress-bar-container"]}">
     <div class="${swalClasses["timer-progress-bar"]}"></div>
   </div>
 </div>
`.replace(/(^|\n)\s*/g, "");
        const resetOldContainer = () => {
          const oldContainer = getContainer();
          if (!oldContainer) {
            return false;
          }
          oldContainer.remove();
          removeClass([document.documentElement, document.body], [
            swalClasses["no-backdrop"],
            swalClasses["toast-shown"],
            // @ts-ignore: 'has-column' is not defined in swalClasses but may be set dynamically
            swalClasses["has-column"]
          ]);
          return true;
        };
        const resetValidationMessage$1 = () => {
          if (globalState.currentInstance) {
            globalState.currentInstance.resetValidationMessage();
          }
        };
        const addInputChangeListeners = () => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          const input = getDirectChildByClass(popup, swalClasses.input);
          const file = getDirectChildByClass(popup, swalClasses.file);
          const range = popup.querySelector(`.${swalClasses.range} input`);
          const rangeOutput = popup.querySelector(`.${swalClasses.range} output`);
          const select = getDirectChildByClass(popup, swalClasses.select);
          const checkbox = popup.querySelector(`.${swalClasses.checkbox} input`);
          const textarea = getDirectChildByClass(popup, swalClasses.textarea);
          if (input) {
            input.oninput = resetValidationMessage$1;
          }
          if (file) {
            file.onchange = resetValidationMessage$1;
          }
          if (select) {
            select.onchange = resetValidationMessage$1;
          }
          if (checkbox) {
            checkbox.onchange = resetValidationMessage$1;
          }
          if (textarea) {
            textarea.oninput = resetValidationMessage$1;
          }
          if (range && rangeOutput) {
            range.oninput = () => {
              resetValidationMessage$1();
              rangeOutput.value = range.value;
            };
            range.onchange = () => {
              resetValidationMessage$1();
              rangeOutput.value = range.value;
            };
          }
        };
        const getTarget = (target) => {
          if (typeof target === "string") {
            const element = document.querySelector(target);
            if (!element) {
              throw new Error(`Target element "${target}" not found`);
            }
            return (
              /** @type {HTMLElement} */
              element
            );
          }
          return target;
        };
        const setupAccessibility = (params) => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          popup.setAttribute("role", params.toast ? "alert" : "dialog");
          popup.setAttribute("aria-live", params.toast ? "polite" : "assertive");
          if (!params.toast) {
            popup.setAttribute("aria-modal", "true");
          }
        };
        const setupRTL = (targetElement) => {
          if (window.getComputedStyle(targetElement).direction === "rtl") {
            addClass(getContainer(), swalClasses.rtl);
            globalState.isRTL = true;
          }
        };
        const init = (params) => {
          const oldContainerExisted = resetOldContainer();
          if (isNodeEnv()) {
            error("SweetAlert2 requires document to initialize");
            return;
          }
          const container = document.createElement("div");
          container.className = swalClasses.container;
          if (oldContainerExisted) {
            addClass(container, swalClasses["no-transition"]);
          }
          setInnerHtml(container, sweetHTML);
          container.dataset["swal2Theme"] = params.theme;
          const targetElement = getTarget(params.target || "body");
          targetElement.appendChild(container);
          if (params.topLayer) {
            container.setAttribute("popover", "");
            container.showPopover();
          }
          setupAccessibility(params);
          setupRTL(targetElement);
          addInputChangeListeners();
        };
        const parseHtmlToContainer = (param, target) => {
          if (param instanceof HTMLElement) {
            target.appendChild(param);
          } else if (typeof param === "object") {
            handleObject(param, target);
          } else if (param) {
            setInnerHtml(target, param);
          }
        };
        const handleObject = (param, target) => {
          if ("jquery" in param) {
            handleJqueryElem(target, param);
          } else {
            setInnerHtml(target, param.toString());
          }
        };
        const handleJqueryElem = (target, elem) => {
          target.textContent = "";
          if (0 in elem) {
            for (let i = 0; i in elem; i++) {
              target.appendChild(elem[i].cloneNode(true));
            }
          } else {
            target.appendChild(elem.cloneNode(true));
          }
        };
        const renderActions = (instance, params) => {
          const actions = getActions();
          const loader = getLoader();
          if (!actions || !loader) {
            return;
          }
          if (!params.showConfirmButton && !params.showDenyButton && !params.showCancelButton) {
            hide(actions);
          } else {
            show(actions);
          }
          applyCustomClass(actions, params, "actions");
          renderButtons(actions, loader, params);
          setInnerHtml(loader, params.loaderHtml || "");
          applyCustomClass(loader, params, "loader");
        };
        function renderButtons(actions, loader, params) {
          const confirmButton = getConfirmButton();
          const denyButton = getDenyButton();
          const cancelButton = getCancelButton();
          if (!confirmButton || !denyButton || !cancelButton) {
            return;
          }
          renderButton(confirmButton, "confirm", params);
          renderButton(denyButton, "deny", params);
          renderButton(cancelButton, "cancel", params);
          handleButtonsStyling(confirmButton, denyButton, cancelButton, params);
          if (params.reverseButtons) {
            if (params.toast) {
              actions.insertBefore(cancelButton, confirmButton);
              actions.insertBefore(denyButton, confirmButton);
            } else {
              actions.insertBefore(cancelButton, loader);
              actions.insertBefore(denyButton, loader);
              actions.insertBefore(confirmButton, loader);
            }
          }
        }
        function handleButtonsStyling(confirmButton, denyButton, cancelButton, params) {
          if (!params.buttonsStyling) {
            removeClass([confirmButton, denyButton, cancelButton], swalClasses.styled);
            return;
          }
          addClass([confirmButton, denyButton, cancelButton], swalClasses.styled);
          if (params.confirmButtonColor) {
            confirmButton.style.setProperty("--swal2-confirm-button-background-color", params.confirmButtonColor);
          }
          if (params.denyButtonColor) {
            denyButton.style.setProperty("--swal2-deny-button-background-color", params.denyButtonColor);
          }
          if (params.cancelButtonColor) {
            cancelButton.style.setProperty("--swal2-cancel-button-background-color", params.cancelButtonColor);
          }
          applyOutlineColor(confirmButton);
          applyOutlineColor(denyButton);
          applyOutlineColor(cancelButton);
        }
        function applyOutlineColor(button) {
          const buttonStyle = window.getComputedStyle(button);
          if (buttonStyle.getPropertyValue("--swal2-action-button-focus-box-shadow")) {
            return;
          }
          const outlineColor = buttonStyle.backgroundColor.replace(/rgba?\((\d+), (\d+), (\d+).*/, "rgba($1, $2, $3, 0.5)");
          button.style.setProperty("--swal2-action-button-focus-box-shadow", buttonStyle.getPropertyValue("--swal2-outline").replace(/ rgba\(.*/, ` ${outlineColor}`));
        }
        function renderButton(button, buttonType, params) {
          const buttonName = (
            /** @type {'Confirm' | 'Deny' | 'Cancel'} */
            capitalizeFirstLetter(buttonType)
          );
          toggle(button, params[`show${buttonName}Button`], "inline-block");
          setInnerHtml(button, params[`${buttonType}ButtonText`] || "");
          button.setAttribute("aria-label", params[`${buttonType}ButtonAriaLabel`] || "");
          button.className = swalClasses[buttonType];
          applyCustomClass(button, params, `${buttonType}Button`);
        }
        const renderCloseButton = (instance, params) => {
          const closeButton = getCloseButton();
          if (!closeButton) {
            return;
          }
          setInnerHtml(closeButton, params.closeButtonHtml || "");
          applyCustomClass(closeButton, params, "closeButton");
          toggle(closeButton, params.showCloseButton);
          closeButton.setAttribute("aria-label", params.closeButtonAriaLabel || "");
        };
        const renderContainer = (instance, params) => {
          const container = getContainer();
          if (!container) {
            return;
          }
          handleBackdropParam(container, params.backdrop);
          handlePositionParam(container, params.position);
          handleGrowParam(container, params.grow);
          applyCustomClass(container, params, "container");
        };
        function handleBackdropParam(container, backdrop) {
          if (typeof backdrop === "string") {
            container.style.background = backdrop;
          } else if (!backdrop) {
            addClass([document.documentElement, document.body], swalClasses["no-backdrop"]);
          }
        }
        function handlePositionParam(container, position) {
          if (!position) {
            return;
          }
          if (position in swalClasses) {
            addClass(container, swalClasses[position]);
          } else {
            warn('The "position" parameter is not valid, defaulting to "center"');
            addClass(container, swalClasses.center);
          }
        }
        function handleGrowParam(container, grow) {
          if (!grow) {
            return;
          }
          addClass(container, swalClasses[`grow-${grow}`]);
        }
        var privateProps = {
          innerParams: /* @__PURE__ */ new WeakMap(),
          domCache: /* @__PURE__ */ new WeakMap()
        };
        const inputClasses = ["input", "file", "range", "select", "radio", "checkbox", "textarea"];
        const renderInput = (instance, params) => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          const innerParams = privateProps.innerParams.get(instance);
          const rerender = !innerParams || params.input !== innerParams.input;
          inputClasses.forEach((inputClass) => {
            const inputContainer = getDirectChildByClass(popup, swalClasses[inputClass]);
            if (!inputContainer) {
              return;
            }
            setAttributes(inputClass, params.inputAttributes);
            inputContainer.className = swalClasses[inputClass];
            if (rerender) {
              hide(inputContainer);
            }
          });
          if (params.input) {
            if (rerender) {
              showInput(params);
            }
            setCustomClass(params);
          }
        };
        const showInput = (params) => {
          if (!params.input) {
            return;
          }
          if (!renderInputType[params.input]) {
            error(`Unexpected type of input! Expected ${Object.keys(renderInputType).join(" | ")}, got "${params.input}"`);
            return;
          }
          const inputContainer = getInputContainer(params.input);
          if (!inputContainer) {
            return;
          }
          const input = renderInputType[params.input](inputContainer, params);
          show(inputContainer);
          if (params.inputAutoFocus) {
            setTimeout(() => {
              focusInput(input);
            });
          }
        };
        const removeAttributes = (input) => {
          for (let i = 0; i < input.attributes.length; i++) {
            const attrName = input.attributes[i].name;
            if (!["id", "type", "value", "style"].includes(attrName)) {
              input.removeAttribute(attrName);
            }
          }
        };
        const setAttributes = (inputClass, inputAttributes) => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          const input = getInput$1(popup, inputClass);
          if (!input) {
            return;
          }
          removeAttributes(input);
          for (const attr in inputAttributes) {
            input.setAttribute(attr, inputAttributes[attr]);
          }
        };
        const setCustomClass = (params) => {
          if (!params.input) {
            return;
          }
          const inputContainer = getInputContainer(params.input);
          if (inputContainer) {
            applyCustomClass(inputContainer, params, "input");
          }
        };
        const setInputPlaceholder = (input, params) => {
          if (!input.placeholder && params.inputPlaceholder) {
            input.placeholder = params.inputPlaceholder;
          }
        };
        const setInputLabel = (input, prependTo, params) => {
          if (params.inputLabel) {
            const label = document.createElement("label");
            const labelClass = swalClasses["input-label"];
            label.setAttribute("for", input.id);
            label.className = labelClass;
            if (typeof params.customClass === "object") {
              addClass(label, params.customClass.inputLabel);
            }
            label.innerText = params.inputLabel;
            prependTo.insertAdjacentElement("beforebegin", label);
          }
        };
        const getInputContainer = (inputType) => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          return getDirectChildByClass(popup, swalClasses[
            /** @type {SwalClass} */
            inputType
          ] || swalClasses.input);
        };
        const checkAndSetInputValue = (input, inputValue) => {
          if (["string", "number"].includes(typeof inputValue)) {
            input.value = `${inputValue}`;
          } else if (!isPromise(inputValue)) {
            warn(`Unexpected type of inputValue! Expected "string", "number" or "Promise", got "${typeof inputValue}"`);
          }
        };
        const renderInputType = {};
        renderInputType.text = renderInputType.email = renderInputType.password = renderInputType.number = renderInputType.tel = renderInputType.url = renderInputType.search = renderInputType.date = renderInputType["datetime-local"] = renderInputType.time = renderInputType.week = renderInputType.month = /** @type {(input: Input | HTMLElement, params: SweetAlertOptions) => Input} */
        (input, params) => {
          const inputElement = (
            /** @type {HTMLInputElement} */
            input
          );
          checkAndSetInputValue(inputElement, params.inputValue);
          setInputLabel(inputElement, inputElement, params);
          setInputPlaceholder(inputElement, params);
          inputElement.type = /** @type {string} */
          params.input;
          return inputElement;
        };
        renderInputType.file = (input, params) => {
          const inputElement = (
            /** @type {HTMLInputElement} */
            input
          );
          setInputLabel(inputElement, inputElement, params);
          setInputPlaceholder(inputElement, params);
          return inputElement;
        };
        renderInputType.range = (range, params) => {
          const rangeContainer = (
            /** @type {HTMLElement} */
            range
          );
          const rangeInput = rangeContainer.querySelector("input");
          const rangeOutput = rangeContainer.querySelector("output");
          if (rangeInput) {
            checkAndSetInputValue(rangeInput, params.inputValue);
            rangeInput.type = /** @type {string} */
            params.input;
            setInputLabel(
              rangeInput,
              /** @type {Input} */
              range,
              params
            );
          }
          if (rangeOutput) {
            checkAndSetInputValue(rangeOutput, params.inputValue);
          }
          return (
            /** @type {Input} */
            range
          );
        };
        renderInputType.select = (select, params) => {
          const selectElement = (
            /** @type {HTMLSelectElement} */
            select
          );
          selectElement.textContent = "";
          if (params.inputPlaceholder) {
            const placeholder = document.createElement("option");
            setInnerHtml(placeholder, params.inputPlaceholder);
            placeholder.value = "";
            placeholder.disabled = true;
            placeholder.selected = true;
            selectElement.appendChild(placeholder);
          }
          setInputLabel(selectElement, selectElement, params);
          return selectElement;
        };
        renderInputType.radio = (radio) => {
          const radioElement = (
            /** @type {HTMLElement} */
            radio
          );
          radioElement.textContent = "";
          return (
            /** @type {Input} */
            radio
          );
        };
        renderInputType.checkbox = (checkboxContainer, params) => {
          const popup = getPopup();
          if (!popup) {
            throw new Error("Popup not found");
          }
          const checkbox = getInput$1(popup, "checkbox");
          if (!checkbox) {
            throw new Error("Checkbox input not found");
          }
          checkbox.value = "1";
          checkbox.checked = Boolean(params.inputValue);
          const containerElement = (
            /** @type {HTMLElement} */
            checkboxContainer
          );
          const label = containerElement.querySelector("span");
          if (label) {
            const placeholderOrLabel = params.inputPlaceholder || params.inputLabel;
            if (placeholderOrLabel) {
              setInnerHtml(label, placeholderOrLabel);
            }
          }
          return checkbox;
        };
        renderInputType.textarea = (textarea, params) => {
          const textareaElement = (
            /** @type {HTMLTextAreaElement} */
            textarea
          );
          checkAndSetInputValue(textareaElement, params.inputValue);
          setInputPlaceholder(textareaElement, params);
          setInputLabel(textareaElement, textareaElement, params);
          const getMargin = (el) => parseInt(window.getComputedStyle(el).marginLeft) + parseInt(window.getComputedStyle(el).marginRight);
          setTimeout(() => {
            if ("MutationObserver" in window) {
              const popup = getPopup();
              if (!popup) {
                return;
              }
              const initialPopupWidth = parseInt(window.getComputedStyle(popup).width);
              const textareaResizeHandler = () => {
                if (!document.body.contains(textareaElement)) {
                  return;
                }
                const textareaWidth = textareaElement.offsetWidth + getMargin(textareaElement);
                const popupElement = getPopup();
                if (popupElement) {
                  if (textareaWidth > initialPopupWidth) {
                    popupElement.style.width = `${textareaWidth}px`;
                  } else {
                    applyNumericalStyle(popupElement, "width", params.width);
                  }
                }
              };
              new MutationObserver(textareaResizeHandler).observe(textareaElement, {
                attributes: true,
                attributeFilter: ["style"]
              });
            }
          });
          return textareaElement;
        };
        const renderContent = (instance, params) => {
          const htmlContainer = getHtmlContainer();
          if (!htmlContainer) {
            return;
          }
          showWhenInnerHtmlPresent(htmlContainer);
          applyCustomClass(htmlContainer, params, "htmlContainer");
          if (params.html) {
            parseHtmlToContainer(params.html, htmlContainer);
            show(htmlContainer, "block");
          } else if (params.text) {
            htmlContainer.textContent = params.text;
            show(htmlContainer, "block");
          } else {
            hide(htmlContainer);
          }
          renderInput(instance, params);
        };
        const renderFooter = (instance, params) => {
          const footer = getFooter();
          if (!footer) {
            return;
          }
          showWhenInnerHtmlPresent(footer);
          toggle(footer, Boolean(params.footer), "block");
          if (params.footer) {
            parseHtmlToContainer(params.footer, footer);
          }
          applyCustomClass(footer, params, "footer");
        };
        const renderIcon = (instance, params) => {
          const innerParams = privateProps.innerParams.get(instance);
          const icon = getIcon();
          if (!icon) {
            return;
          }
          if (innerParams && params.icon === innerParams.icon) {
            setContent(icon, params);
            applyStyles(icon, params);
            return;
          }
          if (!params.icon && !params.iconHtml) {
            hide(icon);
            return;
          }
          if (params.icon && Object.keys(iconTypes).indexOf(params.icon) === -1) {
            error(`Unknown icon! Expected "success", "error", "warning", "info" or "question", got "${params.icon}"`);
            hide(icon);
            return;
          }
          show(icon);
          setContent(icon, params);
          applyStyles(icon, params);
          addClass(icon, params.showClass && params.showClass.icon);
          const colorSchemeQueryList = window.matchMedia("(prefers-color-scheme: dark)");
          colorSchemeQueryList.addEventListener("change", adjustSuccessIconBackgroundColor);
        };
        const applyStyles = (icon, params) => {
          for (const [iconType, iconClassName] of Object.entries(iconTypes)) {
            if (params.icon !== iconType) {
              removeClass(icon, iconClassName);
            }
          }
          addClass(icon, params.icon && iconTypes[params.icon]);
          setColor(icon, params);
          adjustSuccessIconBackgroundColor();
          applyCustomClass(icon, params, "icon");
        };
        const adjustSuccessIconBackgroundColor = () => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          const popupBackgroundColor = window.getComputedStyle(popup).getPropertyValue("background-color");
          const successIconParts = popup.querySelectorAll("[class^=swal2-success-circular-line], .swal2-success-fix");
          for (let i = 0; i < successIconParts.length; i++) {
            successIconParts[i].style.backgroundColor = popupBackgroundColor;
          }
        };
        const successIconHtml = (params) => `
  ${params.animation ? '<div class="swal2-success-circular-line-left"></div>' : ""}
  <span class="swal2-success-line-tip"></span> <span class="swal2-success-line-long"></span>
  <div class="swal2-success-ring"></div>
  ${params.animation ? '<div class="swal2-success-fix"></div>' : ""}
  ${params.animation ? '<div class="swal2-success-circular-line-right"></div>' : ""}
`;
        const errorIconHtml = `
  <span class="swal2-x-mark">
    <span class="swal2-x-mark-line-left"></span>
    <span class="swal2-x-mark-line-right"></span>
  </span>
`;
        const setContent = (icon, params) => {
          if (!params.icon && !params.iconHtml) {
            return;
          }
          let oldContent = icon.innerHTML;
          let newContent = "";
          if (params.iconHtml) {
            newContent = iconContent(params.iconHtml);
          } else if (params.icon === "success") {
            newContent = successIconHtml(params);
            oldContent = oldContent.replace(/ style=".*?"/g, "");
          } else if (params.icon === "error") {
            newContent = errorIconHtml;
          } else if (params.icon) {
            const defaultIconHtml = {
              question: "?",
              warning: "!",
              info: "i"
            };
            newContent = iconContent(defaultIconHtml[params.icon]);
          }
          if (oldContent.trim() !== newContent.trim()) {
            setInnerHtml(icon, newContent);
          }
        };
        const setColor = (icon, params) => {
          if (!params.iconColor) {
            return;
          }
          icon.style.color = params.iconColor;
          icon.style.borderColor = params.iconColor;
          for (const sel of [".swal2-success-line-tip", ".swal2-success-line-long", ".swal2-x-mark-line-left", ".swal2-x-mark-line-right"]) {
            setStyle(icon, sel, "background-color", params.iconColor);
          }
          setStyle(icon, ".swal2-success-ring", "border-color", params.iconColor);
        };
        const iconContent = (content) => `<div class="${swalClasses["icon-content"]}">${content}</div>`;
        const renderImage = (instance, params) => {
          const image = getImage();
          if (!image) {
            return;
          }
          if (!params.imageUrl) {
            hide(image);
            return;
          }
          show(image, "");
          image.setAttribute("src", params.imageUrl);
          image.setAttribute("alt", params.imageAlt || "");
          applyNumericalStyle(image, "width", params.imageWidth);
          applyNumericalStyle(image, "height", params.imageHeight);
          image.className = swalClasses.image;
          applyCustomClass(image, params, "image");
        };
        let dragging = false;
        let mousedownX = 0;
        let mousedownY = 0;
        let initialX = 0;
        let initialY = 0;
        const addDraggableListeners = (popup) => {
          popup.addEventListener("mousedown", down);
          document.body.addEventListener("mousemove", move);
          popup.addEventListener("mouseup", up);
          popup.addEventListener("touchstart", down);
          document.body.addEventListener("touchmove", move);
          popup.addEventListener("touchend", up);
        };
        const removeDraggableListeners = (popup) => {
          popup.removeEventListener("mousedown", down);
          document.body.removeEventListener("mousemove", move);
          popup.removeEventListener("mouseup", up);
          popup.removeEventListener("touchstart", down);
          document.body.removeEventListener("touchmove", move);
          popup.removeEventListener("touchend", up);
        };
        const down = (event) => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          const icon = getIcon();
          if (event.target === popup || icon && icon.contains(
            /** @type {HTMLElement} */
            event.target
          )) {
            dragging = true;
            const clientXY = getClientXY(event);
            mousedownX = clientXY.clientX;
            mousedownY = clientXY.clientY;
            initialX = parseInt(popup.style.insetInlineStart) || 0;
            initialY = parseInt(popup.style.insetBlockStart) || 0;
            addClass(popup, "swal2-dragging");
          }
        };
        const move = (event) => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          if (dragging) {
            let {
              clientX,
              clientY
            } = getClientXY(event);
            const deltaX = clientX - mousedownX;
            popup.style.insetInlineStart = `${initialX + (globalState.isRTL ? -deltaX : deltaX)}px`;
            popup.style.insetBlockStart = `${initialY + (clientY - mousedownY)}px`;
          }
        };
        const up = () => {
          const popup = getPopup();
          dragging = false;
          removeClass(popup, "swal2-dragging");
        };
        const getClientXY = (event) => {
          let clientX = 0, clientY = 0;
          if (event.type.startsWith("mouse")) {
            clientX = /** @type {MouseEvent} */
            event.clientX;
            clientY = /** @type {MouseEvent} */
            event.clientY;
          } else if (event.type.startsWith("touch")) {
            clientX = /** @type {TouchEvent} */
            event.touches[0].clientX;
            clientY = /** @type {TouchEvent} */
            event.touches[0].clientY;
          }
          return {
            clientX,
            clientY
          };
        };
        const renderPopup = (instance, params) => {
          const container = getContainer();
          const popup = getPopup();
          if (!container || !popup) {
            return;
          }
          if (params.toast) {
            applyNumericalStyle(container, "width", params.width);
            popup.style.width = "100%";
            const loader = getLoader();
            if (loader) {
              popup.insertBefore(loader, getIcon());
            }
          } else {
            applyNumericalStyle(popup, "width", params.width);
          }
          applyNumericalStyle(popup, "padding", params.padding);
          if (params.color) {
            popup.style.color = params.color;
          }
          if (params.background) {
            popup.style.background = params.background;
          }
          hide(getValidationMessage());
          addClasses$1(popup, params);
          if (params.draggable && !params.toast) {
            addClass(popup, swalClasses.draggable);
            addDraggableListeners(popup);
          } else {
            removeClass(popup, swalClasses.draggable);
            removeDraggableListeners(popup);
          }
        };
        const addClasses$1 = (popup, params) => {
          const showClass = params.showClass || {};
          popup.className = `${swalClasses.popup} ${isVisible$1(popup) ? showClass.popup : ""}`;
          if (params.toast) {
            addClass([document.documentElement, document.body], swalClasses["toast-shown"]);
            addClass(popup, swalClasses.toast);
          } else {
            addClass(popup, swalClasses.modal);
          }
          applyCustomClass(popup, params, "popup");
          if (typeof params.customClass === "string") {
            addClass(popup, params.customClass);
          }
          if (params.icon) {
            addClass(popup, swalClasses[`icon-${params.icon}`]);
          }
        };
        const renderProgressSteps = (instance, params) => {
          const progressStepsContainer = getProgressSteps();
          if (!progressStepsContainer) {
            return;
          }
          const {
            progressSteps,
            currentProgressStep
          } = params;
          if (!progressSteps || progressSteps.length === 0 || currentProgressStep === void 0) {
            hide(progressStepsContainer);
            return;
          }
          show(progressStepsContainer);
          progressStepsContainer.textContent = "";
          if (currentProgressStep >= progressSteps.length) {
            warn("Invalid currentProgressStep parameter, it should be less than progressSteps.length (currentProgressStep like JS arrays starts from 0)");
          }
          progressSteps.forEach((step, index) => {
            const stepEl = createStepElement(step);
            progressStepsContainer.appendChild(stepEl);
            if (index === currentProgressStep) {
              addClass(stepEl, swalClasses["active-progress-step"]);
            }
            if (index !== progressSteps.length - 1) {
              const lineEl = createLineElement(params);
              progressStepsContainer.appendChild(lineEl);
            }
          });
        };
        const createStepElement = (step) => {
          const stepEl = document.createElement("li");
          addClass(stepEl, swalClasses["progress-step"]);
          setInnerHtml(stepEl, step);
          return stepEl;
        };
        const createLineElement = (params) => {
          const lineEl = document.createElement("li");
          addClass(lineEl, swalClasses["progress-step-line"]);
          if (params.progressStepsDistance) {
            applyNumericalStyle(lineEl, "width", params.progressStepsDistance);
          }
          return lineEl;
        };
        const renderTitle = (instance, params) => {
          const title = getTitle();
          if (!title) {
            return;
          }
          showWhenInnerHtmlPresent(title);
          toggle(title, Boolean(params.title || params.titleText), "block");
          if (params.title) {
            parseHtmlToContainer(params.title, title);
          }
          if (params.titleText) {
            title.innerText = params.titleText;
          }
          applyCustomClass(title, params, "title");
        };
        const render = (instance, params) => {
          var _globalState$eventEmi;
          renderPopup(instance, params);
          renderContainer(instance, params);
          renderProgressSteps(instance, params);
          renderIcon(instance, params);
          renderImage(instance, params);
          renderTitle(instance, params);
          renderCloseButton(instance, params);
          renderContent(instance, params);
          renderActions(instance, params);
          renderFooter(instance, params);
          const popup = getPopup();
          if (typeof params.didRender === "function" && popup) {
            params.didRender(popup);
          }
          (_globalState$eventEmi = globalState.eventEmitter) === null || _globalState$eventEmi === void 0 || _globalState$eventEmi.emit("didRender", popup);
        };
        const isVisible = () => {
          return isVisible$1(getPopup());
        };
        const clickConfirm = () => {
          var _dom$getConfirmButton;
          return (_dom$getConfirmButton = getConfirmButton()) === null || _dom$getConfirmButton === void 0 ? void 0 : _dom$getConfirmButton.click();
        };
        const clickDeny = () => {
          var _dom$getDenyButton;
          return (_dom$getDenyButton = getDenyButton()) === null || _dom$getDenyButton === void 0 ? void 0 : _dom$getDenyButton.click();
        };
        const clickCancel = () => {
          var _dom$getCancelButton;
          return (_dom$getCancelButton = getCancelButton()) === null || _dom$getCancelButton === void 0 ? void 0 : _dom$getCancelButton.click();
        };
        const DismissReason = Object.freeze({
          cancel: "cancel",
          backdrop: "backdrop",
          close: "close",
          esc: "esc",
          timer: "timer"
        });
        const removeKeydownHandler = (globalState2) => {
          if (globalState2.keydownTarget && globalState2.keydownHandlerAdded && globalState2.keydownHandler) {
            const handler = (
              /** @type {EventListenerOrEventListenerObject} */
              /** @type {unknown} */
              globalState2.keydownHandler
            );
            globalState2.keydownTarget.removeEventListener("keydown", handler, {
              capture: globalState2.keydownListenerCapture
            });
            globalState2.keydownHandlerAdded = false;
          }
        };
        const addKeydownHandler = (globalState2, innerParams, dismissWith) => {
          removeKeydownHandler(globalState2);
          if (!innerParams.toast) {
            const handler = (e) => keydownHandler(innerParams, e, dismissWith);
            globalState2.keydownHandler = handler;
            const target = innerParams.keydownListenerCapture ? window : getPopup();
            if (target) {
              globalState2.keydownTarget = target;
              globalState2.keydownListenerCapture = innerParams.keydownListenerCapture;
              const eventHandler = (
                /** @type {EventListenerOrEventListenerObject} */
                /** @type {unknown} */
                handler
              );
              globalState2.keydownTarget.addEventListener("keydown", eventHandler, {
                capture: globalState2.keydownListenerCapture
              });
              globalState2.keydownHandlerAdded = true;
            }
          }
        };
        const setFocus = (index, increment) => {
          var _dom$getPopup;
          const focusableElements = getFocusableElements();
          if (focusableElements.length) {
            index = index + increment;
            if (index === -2) {
              index = focusableElements.length - 1;
            }
            if (index === focusableElements.length) {
              index = 0;
            } else if (index === -1) {
              index = focusableElements.length - 1;
            }
            focusableElements[index].focus();
            return;
          }
          (_dom$getPopup = getPopup()) === null || _dom$getPopup === void 0 || _dom$getPopup.focus();
        };
        const arrowKeysNextButton = ["ArrowRight", "ArrowDown"];
        const arrowKeysPreviousButton = ["ArrowLeft", "ArrowUp"];
        const keydownHandler = (innerParams, event, dismissWith) => {
          if (!innerParams) {
            return;
          }
          if (event.isComposing || event.keyCode === 229) {
            return;
          }
          if (innerParams.stopKeydownPropagation) {
            event.stopPropagation();
          }
          if (event.key === "Enter") {
            handleEnter(event, innerParams);
          } else if (event.key === "Tab") {
            handleTab(event);
          } else if ([...arrowKeysNextButton, ...arrowKeysPreviousButton].includes(event.key)) {
            handleArrows(event.key);
          } else if (event.key === "Escape") {
            handleEsc(event, innerParams, dismissWith);
          }
        };
        const handleEnter = (event, innerParams) => {
          if (!callIfFunction(innerParams.allowEnterKey)) {
            return;
          }
          const popup = getPopup();
          if (!popup || !innerParams.input) {
            return;
          }
          const input = getInput$1(popup, innerParams.input);
          if (event.target && input && event.target instanceof HTMLElement && event.target.outerHTML === input.outerHTML) {
            if (["textarea", "file"].includes(innerParams.input)) {
              return;
            }
            clickConfirm();
            event.preventDefault();
          }
        };
        const handleTab = (event) => {
          const targetElement = event.target;
          const focusableElements = getFocusableElements();
          let btnIndex = -1;
          for (let i = 0; i < focusableElements.length; i++) {
            if (targetElement === focusableElements[i]) {
              btnIndex = i;
              break;
            }
          }
          if (!event.shiftKey) {
            setFocus(btnIndex, 1);
          } else {
            setFocus(btnIndex, -1);
          }
          event.stopPropagation();
          event.preventDefault();
        };
        const handleArrows = (key) => {
          const actions = getActions();
          const confirmButton = getConfirmButton();
          const denyButton = getDenyButton();
          const cancelButton = getCancelButton();
          if (!actions || !confirmButton || !denyButton || !cancelButton) {
            return;
          }
          const buttons = [confirmButton, denyButton, cancelButton];
          if (document.activeElement instanceof HTMLElement && !buttons.includes(document.activeElement)) {
            return;
          }
          const sibling = arrowKeysNextButton.includes(key) ? "nextElementSibling" : "previousElementSibling";
          let buttonToFocus = document.activeElement;
          if (!buttonToFocus) {
            return;
          }
          for (let i = 0; i < actions.children.length; i++) {
            buttonToFocus = buttonToFocus[sibling];
            if (!buttonToFocus) {
              return;
            }
            if (buttonToFocus instanceof HTMLButtonElement && isVisible$1(buttonToFocus)) {
              break;
            }
          }
          if (buttonToFocus instanceof HTMLButtonElement) {
            buttonToFocus.focus();
          }
        };
        const handleEsc = (event, innerParams, dismissWith) => {
          event.preventDefault();
          if (callIfFunction(innerParams.allowEscapeKey)) {
            dismissWith(DismissReason.esc);
          }
        };
        var privateMethods = {
          swalPromiseResolve: /* @__PURE__ */ new WeakMap(),
          swalPromiseReject: /* @__PURE__ */ new WeakMap()
        };
        const setAriaHidden = () => {
          const container = getContainer();
          const bodyChildren = Array.from(document.body.children);
          bodyChildren.forEach((el) => {
            if (el.contains(container)) {
              return;
            }
            if (el.hasAttribute("aria-hidden")) {
              el.setAttribute("data-previous-aria-hidden", el.getAttribute("aria-hidden") || "");
            }
            el.setAttribute("aria-hidden", "true");
          });
        };
        const unsetAriaHidden = () => {
          const bodyChildren = Array.from(document.body.children);
          bodyChildren.forEach((el) => {
            if (el.hasAttribute("data-previous-aria-hidden")) {
              el.setAttribute("aria-hidden", el.getAttribute("data-previous-aria-hidden") || "");
              el.removeAttribute("data-previous-aria-hidden");
            } else {
              el.removeAttribute("aria-hidden");
            }
          });
        };
        const isSafariOrIOS = typeof window !== "undefined" && Boolean(window.GestureEvent);
        const iOSfix = () => {
          if (isSafariOrIOS && !hasClass(document.body, swalClasses.iosfix)) {
            const offset = document.body.scrollTop;
            document.body.style.top = `${offset * -1}px`;
            addClass(document.body, swalClasses.iosfix);
            lockBodyScroll();
          }
        };
        const lockBodyScroll = () => {
          const container = getContainer();
          if (!container) {
            return;
          }
          let preventTouchMove;
          container.ontouchstart = (event) => {
            preventTouchMove = shouldPreventTouchMove(event);
          };
          container.ontouchmove = (event) => {
            if (preventTouchMove) {
              event.preventDefault();
              event.stopPropagation();
            }
          };
        };
        const shouldPreventTouchMove = (event) => {
          const target = event.target;
          const container = getContainer();
          const htmlContainer = getHtmlContainer();
          if (!container || !htmlContainer) {
            return false;
          }
          if (isStylus(event) || isZoom(event)) {
            return false;
          }
          if (target === container) {
            return true;
          }
          if (!isScrollable(container) && target instanceof HTMLElement && !selfOrParentIsScrollable(target, htmlContainer) && // #2823
          target.tagName !== "INPUT" && // #1603
          target.tagName !== "TEXTAREA" && // #2266
          !(isScrollable(htmlContainer) && // #1944
          htmlContainer.contains(target))) {
            return true;
          }
          return false;
        };
        const isStylus = (event) => {
          return Boolean(event.touches && event.touches.length && // @ts-ignore - touchType is not a standard property
          event.touches[0].touchType === "stylus");
        };
        const isZoom = (event) => {
          return event.touches && event.touches.length > 1;
        };
        const undoIOSfix = () => {
          if (hasClass(document.body, swalClasses.iosfix)) {
            const offset = parseInt(document.body.style.top, 10);
            removeClass(document.body, swalClasses.iosfix);
            document.body.style.top = "";
            document.body.scrollTop = offset * -1;
          }
        };
        const measureScrollbar = () => {
          const scrollDiv = document.createElement("div");
          scrollDiv.className = swalClasses["scrollbar-measure"];
          document.body.appendChild(scrollDiv);
          const scrollbarWidth = scrollDiv.getBoundingClientRect().width - scrollDiv.clientWidth;
          document.body.removeChild(scrollDiv);
          return scrollbarWidth;
        };
        let previousBodyPadding = null;
        const replaceScrollbarWithPadding = (initialBodyOverflow) => {
          if (previousBodyPadding !== null) {
            return;
          }
          if (document.body.scrollHeight > window.innerHeight || initialBodyOverflow === "scroll") {
            previousBodyPadding = parseInt(window.getComputedStyle(document.body).getPropertyValue("padding-right"));
            document.body.style.paddingRight = `${previousBodyPadding + measureScrollbar()}px`;
          }
        };
        const undoReplaceScrollbarWithPadding = () => {
          if (previousBodyPadding !== null) {
            document.body.style.paddingRight = `${previousBodyPadding}px`;
            previousBodyPadding = null;
          }
        };
        function removePopupAndResetState(instance, container, returnFocus, didClose) {
          if (isToast()) {
            triggerDidCloseAndDispose(instance, didClose);
          } else {
            restoreActiveElement(returnFocus).then(() => triggerDidCloseAndDispose(instance, didClose));
            removeKeydownHandler(globalState);
          }
          if (isSafariOrIOS) {
            container.setAttribute("style", "display:none !important");
            container.removeAttribute("class");
            container.innerHTML = "";
          } else {
            container.remove();
          }
          if (isModal()) {
            undoReplaceScrollbarWithPadding();
            undoIOSfix();
            unsetAriaHidden();
          }
          removeBodyClasses();
        }
        function removeBodyClasses() {
          removeClass([document.documentElement, document.body], [swalClasses.shown, swalClasses["height-auto"], swalClasses["no-backdrop"], swalClasses["toast-shown"]]);
        }
        function close(resolveValue) {
          resolveValue = prepareResolveValue(resolveValue);
          const swalPromiseResolve = privateMethods.swalPromiseResolve.get(this);
          const didClose = triggerClosePopup(this);
          if (this.isAwaitingPromise) {
            if (!resolveValue.isDismissed) {
              handleAwaitingPromise(this);
              swalPromiseResolve(resolveValue);
            }
          } else if (didClose) {
            swalPromiseResolve(resolveValue);
          }
        }
        const triggerClosePopup = (instance) => {
          const popup = getPopup();
          if (!popup) {
            return false;
          }
          const innerParams = privateProps.innerParams.get(instance);
          if (!innerParams || hasClass(popup, innerParams.hideClass.popup)) {
            return false;
          }
          removeClass(popup, innerParams.showClass.popup);
          addClass(popup, innerParams.hideClass.popup);
          const backdrop = getContainer();
          removeClass(backdrop, innerParams.showClass.backdrop);
          addClass(backdrop, innerParams.hideClass.backdrop);
          handlePopupAnimation(instance, popup, innerParams);
          return true;
        };
        function rejectPromise(error2) {
          const rejectPromise2 = privateMethods.swalPromiseReject.get(this);
          handleAwaitingPromise(this);
          if (rejectPromise2) {
            rejectPromise2(error2);
          }
        }
        const handleAwaitingPromise = (instance) => {
          if (instance.isAwaitingPromise) {
            delete instance.isAwaitingPromise;
            if (!privateProps.innerParams.get(instance)) {
              instance._destroy();
            }
          }
        };
        const prepareResolveValue = (resolveValue) => {
          if (typeof resolveValue === "undefined") {
            return {
              isConfirmed: false,
              isDenied: false,
              isDismissed: true
            };
          }
          return Object.assign({
            isConfirmed: false,
            isDenied: false,
            isDismissed: false
          }, resolveValue);
        };
        const handlePopupAnimation = (instance, popup, innerParams) => {
          var _globalState$eventEmi;
          const container = getContainer();
          const animationIsSupported = hasCssAnimation(popup);
          if (typeof innerParams.willClose === "function") {
            innerParams.willClose(popup);
          }
          (_globalState$eventEmi = globalState.eventEmitter) === null || _globalState$eventEmi === void 0 || _globalState$eventEmi.emit("willClose", popup);
          if (animationIsSupported && container) {
            animatePopup(instance, popup, container, Boolean(innerParams.returnFocus), innerParams.didClose);
          } else if (container) {
            removePopupAndResetState(instance, container, Boolean(innerParams.returnFocus), innerParams.didClose);
          }
        };
        const animatePopup = (instance, popup, container, returnFocus, didClose) => {
          globalState.swalCloseEventFinishedCallback = removePopupAndResetState.bind(null, instance, container, returnFocus, didClose);
          const swalCloseAnimationFinished = function(e) {
            if (e.target === popup) {
              var _globalState$swalClos;
              (_globalState$swalClos = globalState.swalCloseEventFinishedCallback) === null || _globalState$swalClos === void 0 || _globalState$swalClos.call(globalState);
              delete globalState.swalCloseEventFinishedCallback;
              popup.removeEventListener("animationend", swalCloseAnimationFinished);
              popup.removeEventListener("transitionend", swalCloseAnimationFinished);
            }
          };
          popup.addEventListener("animationend", swalCloseAnimationFinished);
          popup.addEventListener("transitionend", swalCloseAnimationFinished);
        };
        const triggerDidCloseAndDispose = (instance, didClose) => {
          setTimeout(() => {
            var _globalState$eventEmi2;
            if (typeof didClose === "function") {
              didClose.bind(instance.params)();
            }
            (_globalState$eventEmi2 = globalState.eventEmitter) === null || _globalState$eventEmi2 === void 0 || _globalState$eventEmi2.emit("didClose");
            if (instance._destroy) {
              instance._destroy();
            }
          });
        };
        const showLoading = (buttonToReplace) => {
          let popup = getPopup();
          if (!popup) {
            new Swal2();
          }
          popup = getPopup();
          if (!popup) {
            return;
          }
          const loader = getLoader();
          if (isToast()) {
            hide(getIcon());
          } else {
            replaceButton(popup, buttonToReplace);
          }
          show(loader);
          popup.setAttribute("data-loading", "true");
          popup.setAttribute("aria-busy", "true");
          popup.focus();
        };
        const replaceButton = (popup, buttonToReplace) => {
          const actions = getActions();
          const loader = getLoader();
          if (!actions || !loader) {
            return;
          }
          if (!buttonToReplace && isVisible$1(getConfirmButton())) {
            buttonToReplace = getConfirmButton();
          }
          show(actions);
          if (buttonToReplace) {
            hide(buttonToReplace);
            loader.setAttribute("data-button-to-replace", buttonToReplace.className);
            actions.insertBefore(loader, buttonToReplace);
          }
          addClass([popup, actions], swalClasses.loading);
        };
        const handleInputOptionsAndValue = (instance, params) => {
          if (params.input === "select" || params.input === "radio") {
            handleInputOptions(instance, params);
          } else if (["text", "email", "number", "tel", "textarea"].some((i) => i === params.input) && (hasToPromiseFn(params.inputValue) || isPromise(params.inputValue))) {
            showLoading(getConfirmButton());
            handleInputValue(instance, params);
          }
        };
        const getInputValue = (instance, innerParams) => {
          const input = instance.getInput();
          if (!input) {
            return null;
          }
          switch (innerParams.input) {
            case "checkbox":
              return getCheckboxValue(input);
            case "radio":
              return getRadioValue(input);
            case "file":
              return getFileValue(input);
            default:
              return innerParams.inputAutoTrim ? input.value.trim() : input.value;
          }
        };
        const getCheckboxValue = (input) => input.checked ? 1 : 0;
        const getRadioValue = (input) => input.checked ? input.value : null;
        const getFileValue = (input) => input.files && input.files.length ? input.getAttribute("multiple") !== null ? input.files : input.files[0] : null;
        const handleInputOptions = (instance, params) => {
          const popup = getPopup();
          if (!popup) {
            return;
          }
          const processInputOptions = (inputOptions) => {
            if (params.input === "select") {
              populateSelectOptions(popup, formatInputOptions(inputOptions), params);
            } else if (params.input === "radio") {
              populateRadioOptions(popup, formatInputOptions(inputOptions), params);
            }
          };
          if (hasToPromiseFn(params.inputOptions) || isPromise(params.inputOptions)) {
            showLoading(getConfirmButton());
            asPromise(params.inputOptions).then((inputOptions) => {
              instance.hideLoading();
              processInputOptions(inputOptions);
            });
          } else if (typeof params.inputOptions === "object") {
            processInputOptions(params.inputOptions);
          } else {
            error(`Unexpected type of inputOptions! Expected object, Map or Promise, got ${typeof params.inputOptions}`);
          }
        };
        const handleInputValue = (instance, params) => {
          const input = instance.getInput();
          if (!input) {
            return;
          }
          hide(input);
          asPromise(params.inputValue).then((inputValue) => {
            input.value = params.input === "number" ? `${parseFloat(inputValue) || 0}` : `${inputValue}`;
            show(input);
            input.focus();
            instance.hideLoading();
          }).catch((err) => {
            error(`Error in inputValue promise: ${err}`);
            input.value = "";
            show(input);
            input.focus();
            instance.hideLoading();
          });
        };
        function populateSelectOptions(popup, inputOptions, params) {
          const select = getDirectChildByClass(popup, swalClasses.select);
          if (!select) {
            return;
          }
          const renderOption = (parent, optionLabel, optionValue) => {
            const option = document.createElement("option");
            option.value = optionValue;
            setInnerHtml(option, optionLabel);
            option.selected = isSelected(optionValue, params.inputValue);
            parent.appendChild(option);
          };
          inputOptions.forEach((inputOption) => {
            const optionValue = inputOption[0];
            const optionLabel = inputOption[1];
            if (Array.isArray(optionLabel)) {
              const optgroup = document.createElement("optgroup");
              optgroup.label = optionValue;
              optgroup.disabled = false;
              select.appendChild(optgroup);
              optionLabel.forEach((o) => renderOption(optgroup, o[1], o[0]));
            } else {
              renderOption(select, optionLabel, optionValue);
            }
          });
          select.focus();
        }
        function populateRadioOptions(popup, inputOptions, params) {
          const radio = getDirectChildByClass(popup, swalClasses.radio);
          if (!radio) {
            return;
          }
          inputOptions.forEach((inputOption) => {
            const radioValue = inputOption[0];
            const radioLabel = inputOption[1];
            const radioInput = document.createElement("input");
            const radioLabelElement = document.createElement("label");
            radioInput.type = "radio";
            radioInput.name = swalClasses.radio;
            radioInput.value = radioValue;
            if (isSelected(radioValue, params.inputValue)) {
              radioInput.checked = true;
            }
            const label = document.createElement("span");
            setInnerHtml(label, radioLabel);
            label.className = swalClasses.label;
            radioLabelElement.appendChild(radioInput);
            radioLabelElement.appendChild(label);
            radio.appendChild(radioLabelElement);
          });
          const radios = radio.querySelectorAll("input");
          if (radios.length) {
            radios[0].focus();
          }
        }
        const formatInputOptions = (inputOptions) => {
          const result = [];
          if (inputOptions instanceof Map) {
            inputOptions.forEach((value, key) => {
              let valueFormatted = value;
              if (typeof valueFormatted === "object") {
                valueFormatted = formatInputOptions(valueFormatted);
              }
              result.push([key, valueFormatted]);
            });
          } else {
            Object.keys(inputOptions).forEach((key) => {
              let valueFormatted = inputOptions[key];
              if (typeof valueFormatted === "object") {
                valueFormatted = formatInputOptions(valueFormatted);
              }
              result.push([key, valueFormatted]);
            });
          }
          return result;
        };
        const isSelected = (optionValue, inputValue) => {
          return Boolean(inputValue) && inputValue !== null && inputValue !== void 0 && inputValue.toString() === optionValue.toString();
        };
        const handleConfirmButtonClick = (instance) => {
          const innerParams = privateProps.innerParams.get(instance);
          instance.disableButtons();
          if (innerParams.input) {
            handleConfirmOrDenyWithInput(instance, "confirm");
          } else {
            confirm(instance, true);
          }
        };
        const handleDenyButtonClick = (instance) => {
          const innerParams = privateProps.innerParams.get(instance);
          instance.disableButtons();
          if (innerParams.returnInputValueOnDeny) {
            handleConfirmOrDenyWithInput(instance, "deny");
          } else {
            deny(instance, false);
          }
        };
        const handleCancelButtonClick = (instance, dismissWith) => {
          instance.disableButtons();
          dismissWith(DismissReason.cancel);
        };
        const handleConfirmOrDenyWithInput = (instance, type) => {
          const innerParams = privateProps.innerParams.get(instance);
          if (!innerParams.input) {
            error(`The "input" parameter is needed to be set when using returnInputValueOn${capitalizeFirstLetter(type)}`);
            return;
          }
          const input = instance.getInput();
          const inputValue = getInputValue(instance, innerParams);
          if (innerParams.inputValidator) {
            handleInputValidator(instance, inputValue, type);
          } else if (input && !input.checkValidity()) {
            instance.enableButtons();
            instance.showValidationMessage(innerParams.validationMessage || input.validationMessage);
          } else if (type === "deny") {
            deny(instance, inputValue);
          } else {
            confirm(instance, inputValue);
          }
        };
        const handleInputValidator = (instance, inputValue, type) => {
          const innerParams = privateProps.innerParams.get(instance);
          instance.disableInput();
          const validationPromise = Promise.resolve().then(() => asPromise(innerParams.inputValidator(inputValue, innerParams.validationMessage)));
          validationPromise.then((validationMessage) => {
            instance.enableButtons();
            instance.enableInput();
            if (validationMessage) {
              instance.showValidationMessage(validationMessage);
            } else if (type === "deny") {
              deny(instance, inputValue);
            } else {
              confirm(instance, inputValue);
            }
          });
        };
        const deny = (instance, value) => {
          const innerParams = privateProps.innerParams.get(instance);
          if (innerParams.showLoaderOnDeny) {
            showLoading(getDenyButton());
          }
          if (innerParams.preDeny) {
            instance.isAwaitingPromise = true;
            const preDenyPromise = Promise.resolve().then(() => asPromise(innerParams.preDeny(value, innerParams.validationMessage)));
            preDenyPromise.then((preDenyValue) => {
              if (preDenyValue === false) {
                instance.hideLoading();
                handleAwaitingPromise(instance);
              } else {
                instance.close(
                  /** @type SweetAlertResult */
                  {
                    isDenied: true,
                    value: typeof preDenyValue === "undefined" ? value : preDenyValue
                  }
                );
              }
            }).catch((error2) => rejectWith(instance, error2));
          } else {
            instance.close(
              /** @type SweetAlertResult */
              {
                isDenied: true,
                value
              }
            );
          }
        };
        const succeedWith = (instance, value) => {
          instance.close(
            /** @type SweetAlertResult */
            {
              isConfirmed: true,
              value
            }
          );
        };
        const rejectWith = (instance, error2) => {
          instance.rejectPromise(error2);
        };
        const confirm = (instance, value) => {
          const innerParams = privateProps.innerParams.get(instance);
          if (innerParams.showLoaderOnConfirm) {
            showLoading();
          }
          if (innerParams.preConfirm) {
            instance.resetValidationMessage();
            instance.isAwaitingPromise = true;
            const preConfirmPromise = Promise.resolve().then(() => asPromise(innerParams.preConfirm(value, innerParams.validationMessage)));
            preConfirmPromise.then((preConfirmValue) => {
              if (isVisible$1(getValidationMessage()) || preConfirmValue === false) {
                instance.hideLoading();
                handleAwaitingPromise(instance);
              } else {
                succeedWith(instance, typeof preConfirmValue === "undefined" ? value : preConfirmValue);
              }
            }).catch((error2) => rejectWith(instance, error2));
          } else {
            succeedWith(instance, value);
          }
        };
        function hideLoading() {
          const innerParams = privateProps.innerParams.get(this);
          if (!innerParams) {
            return;
          }
          const domCache = privateProps.domCache.get(this);
          hide(domCache.loader);
          if (isToast()) {
            if (innerParams.icon) {
              show(getIcon());
            }
          } else {
            showRelatedButton(domCache);
          }
          removeClass([domCache.popup, domCache.actions], swalClasses.loading);
          domCache.popup.removeAttribute("aria-busy");
          domCache.popup.removeAttribute("data-loading");
          domCache.confirmButton.disabled = false;
          domCache.denyButton.disabled = false;
          domCache.cancelButton.disabled = false;
        }
        const showRelatedButton = (domCache) => {
          const dataButtonToReplace = domCache.loader.getAttribute("data-button-to-replace");
          const buttonToReplace = dataButtonToReplace ? domCache.popup.getElementsByClassName(dataButtonToReplace) : [];
          if (buttonToReplace.length) {
            show(
              /** @type {HTMLElement} */
              buttonToReplace[0],
              "inline-block"
            );
          } else if (allButtonsAreHidden()) {
            hide(domCache.actions);
          }
        };
        function getInput() {
          const innerParams = privateProps.innerParams.get(this);
          const domCache = privateProps.domCache.get(this);
          if (!domCache) {
            return null;
          }
          return getInput$1(domCache.popup, innerParams.input);
        }
        function setButtonsDisabled(instance, buttons, disabled) {
          const domCache = privateProps.domCache.get(instance);
          buttons.forEach((button) => {
            domCache[button].disabled = disabled;
          });
        }
        function setInputDisabled(input, disabled) {
          const popup = getPopup();
          if (!popup || !input) {
            return;
          }
          if (input.type === "radio") {
            const radios = popup.querySelectorAll(`[name="${swalClasses.radio}"]`);
            for (let i = 0; i < radios.length; i++) {
              radios[i].disabled = disabled;
            }
          } else {
            input.disabled = disabled;
          }
        }
        function enableButtons() {
          setButtonsDisabled(this, ["confirmButton", "denyButton", "cancelButton"], false);
        }
        function disableButtons() {
          setButtonsDisabled(this, ["confirmButton", "denyButton", "cancelButton"], true);
        }
        function enableInput() {
          setInputDisabled(this.getInput(), false);
        }
        function disableInput() {
          setInputDisabled(this.getInput(), true);
        }
        function showValidationMessage(error2) {
          const domCache = privateProps.domCache.get(this);
          const params = privateProps.innerParams.get(this);
          setInnerHtml(domCache.validationMessage, error2);
          domCache.validationMessage.className = swalClasses["validation-message"];
          if (params.customClass && params.customClass.validationMessage) {
            addClass(domCache.validationMessage, params.customClass.validationMessage);
          }
          show(domCache.validationMessage);
          const input = this.getInput();
          if (input) {
            input.setAttribute("aria-invalid", "true");
            input.setAttribute("aria-describedby", swalClasses["validation-message"]);
            focusInput(input);
            addClass(input, swalClasses.inputerror);
          }
        }
        function resetValidationMessage() {
          const domCache = privateProps.domCache.get(this);
          if (domCache.validationMessage) {
            hide(domCache.validationMessage);
          }
          const input = this.getInput();
          if (input) {
            input.removeAttribute("aria-invalid");
            input.removeAttribute("aria-describedby");
            removeClass(input, swalClasses.inputerror);
          }
        }
        const defaultParams = {
          title: "",
          titleText: "",
          text: "",
          html: "",
          footer: "",
          icon: void 0,
          iconColor: void 0,
          iconHtml: void 0,
          template: void 0,
          toast: false,
          draggable: false,
          animation: true,
          theme: "light",
          showClass: {
            popup: "swal2-show",
            backdrop: "swal2-backdrop-show",
            icon: "swal2-icon-show"
          },
          hideClass: {
            popup: "swal2-hide",
            backdrop: "swal2-backdrop-hide",
            icon: "swal2-icon-hide"
          },
          customClass: {},
          target: "body",
          color: void 0,
          backdrop: true,
          heightAuto: true,
          allowOutsideClick: true,
          allowEscapeKey: true,
          allowEnterKey: true,
          stopKeydownPropagation: true,
          keydownListenerCapture: false,
          showConfirmButton: true,
          showDenyButton: false,
          showCancelButton: false,
          preConfirm: void 0,
          preDeny: void 0,
          confirmButtonText: "OK",
          confirmButtonAriaLabel: "",
          confirmButtonColor: void 0,
          denyButtonText: "No",
          denyButtonAriaLabel: "",
          denyButtonColor: void 0,
          cancelButtonText: "Cancel",
          cancelButtonAriaLabel: "",
          cancelButtonColor: void 0,
          buttonsStyling: true,
          reverseButtons: false,
          focusConfirm: true,
          focusDeny: false,
          focusCancel: false,
          returnFocus: true,
          showCloseButton: false,
          closeButtonHtml: "&times;",
          closeButtonAriaLabel: "Close this dialog",
          loaderHtml: "",
          showLoaderOnConfirm: false,
          showLoaderOnDeny: false,
          imageUrl: void 0,
          imageWidth: void 0,
          imageHeight: void 0,
          imageAlt: "",
          timer: void 0,
          timerProgressBar: false,
          width: void 0,
          padding: void 0,
          background: void 0,
          input: void 0,
          inputPlaceholder: "",
          inputLabel: "",
          inputValue: "",
          inputOptions: {},
          inputAutoFocus: true,
          inputAutoTrim: true,
          inputAttributes: {},
          inputValidator: void 0,
          returnInputValueOnDeny: false,
          validationMessage: void 0,
          grow: false,
          position: "center",
          progressSteps: [],
          currentProgressStep: void 0,
          progressStepsDistance: void 0,
          willOpen: void 0,
          didOpen: void 0,
          didRender: void 0,
          willClose: void 0,
          didClose: void 0,
          didDestroy: void 0,
          scrollbarPadding: true,
          topLayer: false
        };
        const updatableParams = ["allowEscapeKey", "allowOutsideClick", "background", "buttonsStyling", "cancelButtonAriaLabel", "cancelButtonColor", "cancelButtonText", "closeButtonAriaLabel", "closeButtonHtml", "color", "confirmButtonAriaLabel", "confirmButtonColor", "confirmButtonText", "currentProgressStep", "customClass", "denyButtonAriaLabel", "denyButtonColor", "denyButtonText", "didClose", "didDestroy", "draggable", "footer", "hideClass", "html", "icon", "iconColor", "iconHtml", "imageAlt", "imageHeight", "imageUrl", "imageWidth", "preConfirm", "preDeny", "progressSteps", "returnFocus", "reverseButtons", "showCancelButton", "showCloseButton", "showConfirmButton", "showDenyButton", "text", "title", "titleText", "theme", "willClose"];
        const deprecatedParams = {
          allowEnterKey: void 0
        };
        const toastIncompatibleParams = ["allowOutsideClick", "allowEnterKey", "backdrop", "draggable", "focusConfirm", "focusDeny", "focusCancel", "returnFocus", "heightAuto", "keydownListenerCapture"];
        const isValidParameter = (paramName) => {
          return Object.prototype.hasOwnProperty.call(defaultParams, paramName);
        };
        const isUpdatableParameter = (paramName) => {
          return updatableParams.indexOf(paramName) !== -1;
        };
        const isDeprecatedParameter = (paramName) => {
          return deprecatedParams[paramName];
        };
        const checkIfParamIsValid = (param) => {
          if (!isValidParameter(param)) {
            warn(`Unknown parameter "${param}"`);
          }
        };
        const checkIfToastParamIsValid = (param) => {
          if (toastIncompatibleParams.includes(param)) {
            warn(`The parameter "${param}" is incompatible with toasts`);
          }
        };
        const checkIfParamIsDeprecated = (param) => {
          const isDeprecated = isDeprecatedParameter(param);
          if (isDeprecated) {
            warnAboutDeprecation(param, isDeprecated);
          }
        };
        const showWarningsForParams = (params) => {
          if (params.backdrop === false && params.allowOutsideClick) {
            warn('"allowOutsideClick" parameter requires `backdrop` parameter to be set to `true`');
          }
          if (params.theme && !["light", "dark", "auto", "minimal", "borderless", "bootstrap-4", "bootstrap-4-light", "bootstrap-4-dark", "bootstrap-5", "bootstrap-5-light", "bootstrap-5-dark", "material-ui", "material-ui-light", "material-ui-dark", "embed-iframe", "bulma", "bulma-light", "bulma-dark"].includes(params.theme)) {
            warn(`Invalid theme "${params.theme}"`);
          }
          for (const param in params) {
            checkIfParamIsValid(param);
            if (params.toast) {
              checkIfToastParamIsValid(param);
            }
            checkIfParamIsDeprecated(param);
          }
        };
        function update(params) {
          const container = getContainer();
          const popup = getPopup();
          const innerParams = privateProps.innerParams.get(this);
          if (!popup || hasClass(popup, innerParams.hideClass.popup)) {
            warn(`You're trying to update the closed or closing popup, that won't work. Use the update() method in preConfirm parameter or show a new popup.`);
            return;
          }
          const validUpdatableParams = filterValidParams(params);
          const updatedParams = Object.assign({}, innerParams, validUpdatableParams);
          showWarningsForParams(updatedParams);
          if (container) {
            container.dataset["swal2Theme"] = updatedParams.theme;
          }
          render(this, updatedParams);
          privateProps.innerParams.set(this, updatedParams);
          Object.defineProperties(this, {
            params: {
              value: Object.assign({}, this.params, params),
              writable: false,
              enumerable: true
            }
          });
        }
        const filterValidParams = (params) => {
          const validUpdatableParams = {};
          Object.keys(params).forEach((param) => {
            if (isUpdatableParameter(param)) {
              const typedParams = (
                /** @type {Record<string, any>} */
                params
              );
              validUpdatableParams[param] = typedParams[param];
            } else {
              warn(`Invalid parameter to update: ${param}`);
            }
          });
          return validUpdatableParams;
        };
        function _destroy() {
          var _globalState$eventEmi;
          const domCache = privateProps.domCache.get(this);
          const innerParams = privateProps.innerParams.get(this);
          if (!innerParams) {
            disposeWeakMaps(this);
            return;
          }
          if (domCache.popup && globalState.swalCloseEventFinishedCallback) {
            globalState.swalCloseEventFinishedCallback();
            delete globalState.swalCloseEventFinishedCallback;
          }
          if (typeof innerParams.didDestroy === "function") {
            innerParams.didDestroy();
          }
          (_globalState$eventEmi = globalState.eventEmitter) === null || _globalState$eventEmi === void 0 || _globalState$eventEmi.emit("didDestroy");
          disposeSwal(this);
        }
        const disposeSwal = (instance) => {
          disposeWeakMaps(instance);
          delete instance.params;
          delete globalState.keydownHandler;
          delete globalState.keydownTarget;
          delete globalState.currentInstance;
        };
        const disposeWeakMaps = (instance) => {
          if (instance.isAwaitingPromise) {
            unsetWeakMaps(privateProps, instance);
            instance.isAwaitingPromise = true;
          } else {
            unsetWeakMaps(privateMethods, instance);
            unsetWeakMaps(privateProps, instance);
            delete instance.isAwaitingPromise;
            delete instance.disableButtons;
            delete instance.enableButtons;
            delete instance.getInput;
            delete instance.disableInput;
            delete instance.enableInput;
            delete instance.hideLoading;
            delete instance.disableLoading;
            delete instance.showValidationMessage;
            delete instance.resetValidationMessage;
            delete instance.close;
            delete instance.closePopup;
            delete instance.closeModal;
            delete instance.closeToast;
            delete instance.rejectPromise;
            delete instance.update;
            delete instance._destroy;
          }
        };
        const unsetWeakMaps = (obj, instance) => {
          for (const i in obj) {
            obj[i].delete(instance);
          }
        };
        var instanceMethods = /* @__PURE__ */ Object.freeze({
          __proto__: null,
          _destroy,
          close,
          closeModal: close,
          closePopup: close,
          closeToast: close,
          disableButtons,
          disableInput,
          disableLoading: hideLoading,
          enableButtons,
          enableInput,
          getInput,
          handleAwaitingPromise,
          hideLoading,
          rejectPromise,
          resetValidationMessage,
          showValidationMessage,
          update
        });
        const handlePopupClick = (innerParams, domCache, dismissWith) => {
          if (innerParams.toast) {
            handleToastClick(innerParams, domCache, dismissWith);
          } else {
            handleModalMousedown(domCache);
            handleContainerMousedown(domCache);
            handleModalClick(innerParams, domCache, dismissWith);
          }
        };
        const handleToastClick = (innerParams, domCache, dismissWith) => {
          domCache.popup.onclick = () => {
            if (innerParams && (isAnyButtonShown(innerParams) || innerParams.timer || innerParams.input)) {
              return;
            }
            dismissWith(DismissReason.close);
          };
        };
        const isAnyButtonShown = (innerParams) => {
          return Boolean(innerParams.showConfirmButton || innerParams.showDenyButton || innerParams.showCancelButton || innerParams.showCloseButton);
        };
        let ignoreOutsideClick = false;
        const handleModalMousedown = (domCache) => {
          domCache.popup.onmousedown = () => {
            domCache.container.onmouseup = function(e) {
              domCache.container.onmouseup = () => {
              };
              if (e.target === domCache.container) {
                ignoreOutsideClick = true;
              }
            };
          };
        };
        const handleContainerMousedown = (domCache) => {
          domCache.container.onmousedown = (e) => {
            if (e.target === domCache.container) {
              e.preventDefault();
            }
            domCache.popup.onmouseup = function(e2) {
              domCache.popup.onmouseup = () => {
              };
              if (e2.target === domCache.popup || e2.target instanceof HTMLElement && domCache.popup.contains(e2.target)) {
                ignoreOutsideClick = true;
              }
            };
          };
        };
        const handleModalClick = (innerParams, domCache, dismissWith) => {
          domCache.container.onclick = (e) => {
            if (ignoreOutsideClick) {
              ignoreOutsideClick = false;
              return;
            }
            if (e.target === domCache.container && callIfFunction(innerParams.allowOutsideClick)) {
              dismissWith(DismissReason.backdrop);
            }
          };
        };
        const isJqueryElement = (elem) => typeof elem === "object" && elem.jquery;
        const isElement = (elem) => elem instanceof Element || isJqueryElement(elem);
        const argsToParams = (args) => {
          const params = {};
          if (typeof args[0] === "object" && !isElement(args[0])) {
            Object.assign(params, args[0]);
          } else {
            ["title", "html", "icon"].forEach((name, index) => {
              const arg = args[index];
              if (typeof arg === "string" || isElement(arg)) {
                params[name] = arg;
              } else if (arg !== void 0) {
                error(`Unexpected type of ${name}! Expected "string" or "Element", got ${typeof arg}`);
              }
            });
          }
          return params;
        };
        function fire(...args) {
          return new this(...args);
        }
        function mixin(mixinParams) {
          class MixinSwal extends this {
            /**
             * @param {any} params
             * @param {any} priorityMixinParams
             */
            _main(params, priorityMixinParams) {
              return super._main(params, Object.assign({}, mixinParams, priorityMixinParams));
            }
          }
          return MixinSwal;
        }
        const getTimerLeft = () => {
          return globalState.timeout && globalState.timeout.getTimerLeft();
        };
        const stopTimer = () => {
          if (globalState.timeout) {
            stopTimerProgressBar();
            return globalState.timeout.stop();
          }
        };
        const resumeTimer = () => {
          if (globalState.timeout) {
            const remaining = globalState.timeout.start();
            animateTimerProgressBar(remaining);
            return remaining;
          }
        };
        const toggleTimer = () => {
          const timer = globalState.timeout;
          return timer && (timer.running ? stopTimer() : resumeTimer());
        };
        const increaseTimer = (ms) => {
          if (globalState.timeout) {
            const remaining = globalState.timeout.increase(ms);
            animateTimerProgressBar(remaining, true);
            return remaining;
          }
        };
        const isTimerRunning = () => {
          return Boolean(globalState.timeout && globalState.timeout.isRunning());
        };
        let bodyClickListenerAdded = false;
        const clickHandlers = {};
        function bindClickHandler(attr = "data-swal-template") {
          clickHandlers[attr] = this;
          if (!bodyClickListenerAdded) {
            document.body.addEventListener("click", bodyClickListener);
            bodyClickListenerAdded = true;
          }
        }
        const bodyClickListener = (event) => {
          for (let el = (
            /** @type {any} */
            event.target
          ); el && el !== document; el = el.parentNode) {
            for (const attr in clickHandlers) {
              const template = el.getAttribute && el.getAttribute(attr);
              if (template) {
                clickHandlers[attr].fire({
                  template
                });
                return;
              }
            }
          }
        };
        class EventEmitter {
          constructor() {
            this.events = {};
          }
          /**
           * @param {string} eventName
           * @returns {EventHandlers}
           */
          _getHandlersByEventName(eventName) {
            if (typeof this.events[eventName] === "undefined") {
              this.events[eventName] = [];
            }
            return this.events[eventName];
          }
          /**
           * @param {string} eventName
           * @param {EventHandler} eventHandler
           */
          on(eventName, eventHandler) {
            const currentHandlers = this._getHandlersByEventName(eventName);
            if (!currentHandlers.includes(eventHandler)) {
              currentHandlers.push(eventHandler);
            }
          }
          /**
           * @param {string} eventName
           * @param {EventHandler} eventHandler
           */
          once(eventName, eventHandler) {
            const onceFn = (...args) => {
              this.removeListener(eventName, onceFn);
              eventHandler.apply(this, args);
            };
            this.on(eventName, onceFn);
          }
          /**
           * @param {string} eventName
           * @param {...any} args
           */
          emit(eventName, ...args) {
            this._getHandlersByEventName(eventName).forEach(
              /**
               * @param {EventHandler} eventHandler
               */
              (eventHandler) => {
                try {
                  eventHandler.apply(this, args);
                } catch (error2) {
                  console.error(error2);
                }
              }
            );
          }
          /**
           * @param {string} eventName
           * @param {EventHandler} eventHandler
           */
          removeListener(eventName, eventHandler) {
            const currentHandlers = this._getHandlersByEventName(eventName);
            const index = currentHandlers.indexOf(eventHandler);
            if (index > -1) {
              currentHandlers.splice(index, 1);
            }
          }
          /**
           * @param {string} eventName
           */
          removeAllListeners(eventName) {
            if (this.events[eventName] !== void 0) {
              this.events[eventName].length = 0;
            }
          }
          reset() {
            this.events = {};
          }
        }
        globalState.eventEmitter = new EventEmitter();
        const on = (eventName, eventHandler) => {
          if (globalState.eventEmitter) {
            globalState.eventEmitter.on(eventName, eventHandler);
          }
        };
        const once = (eventName, eventHandler) => {
          if (globalState.eventEmitter) {
            globalState.eventEmitter.once(eventName, eventHandler);
          }
        };
        const off = (eventName, eventHandler) => {
          if (!globalState.eventEmitter) {
            return;
          }
          if (!eventName) {
            globalState.eventEmitter.reset();
            return;
          }
          if (eventHandler) {
            globalState.eventEmitter.removeListener(eventName, eventHandler);
          } else {
            globalState.eventEmitter.removeAllListeners(eventName);
          }
        };
        var staticMethods = /* @__PURE__ */ Object.freeze({
          __proto__: null,
          argsToParams,
          bindClickHandler,
          clickCancel,
          clickConfirm,
          clickDeny,
          enableLoading: showLoading,
          fire,
          getActions,
          getCancelButton,
          getCloseButton,
          getConfirmButton,
          getContainer,
          getDenyButton,
          getFocusableElements,
          getFooter,
          getHtmlContainer,
          getIcon,
          getIconContent,
          getImage,
          getInputLabel,
          getLoader,
          getPopup,
          getProgressSteps,
          getTimerLeft,
          getTimerProgressBar,
          getTitle,
          getValidationMessage,
          increaseTimer,
          isDeprecatedParameter,
          isLoading,
          isTimerRunning,
          isUpdatableParameter,
          isValidParameter,
          isVisible,
          mixin,
          off,
          on,
          once,
          resumeTimer,
          showLoading,
          stopTimer,
          toggleTimer
        });
        class Timer {
          /**
           * @param {() => void} callback
           * @param {number} delay
           */
          constructor(callback, delay) {
            this.callback = callback;
            this.remaining = delay;
            this.running = false;
            this.start();
          }
          /**
           * @returns {number}
           */
          start() {
            if (!this.running) {
              this.running = true;
              this.started = /* @__PURE__ */ new Date();
              this.id = setTimeout(this.callback, this.remaining);
            }
            return this.remaining;
          }
          /**
           * @returns {number}
           */
          stop() {
            if (this.started && this.running) {
              this.running = false;
              clearTimeout(this.id);
              this.remaining -= (/* @__PURE__ */ new Date()).getTime() - this.started.getTime();
            }
            return this.remaining;
          }
          /**
           * @param {number} n
           * @returns {number}
           */
          increase(n) {
            const running = this.running;
            if (running) {
              this.stop();
            }
            this.remaining += n;
            if (running) {
              this.start();
            }
            return this.remaining;
          }
          /**
           * @returns {number}
           */
          getTimerLeft() {
            if (this.running) {
              this.stop();
              this.start();
            }
            return this.remaining;
          }
          /**
           * @returns {boolean}
           */
          isRunning() {
            return this.running;
          }
        }
        const swalStringParams = ["swal-title", "swal-html", "swal-footer"];
        const getTemplateParams = (params) => {
          const template = typeof params.template === "string" ? (
            /** @type {HTMLTemplateElement} */
            document.querySelector(params.template)
          ) : params.template;
          if (!template) {
            return {};
          }
          const templateContent = template.content;
          showWarningsForElements(templateContent);
          const result = Object.assign(getSwalParams(templateContent), getSwalFunctionParams(templateContent), getSwalButtons(templateContent), getSwalImage(templateContent), getSwalIcon(templateContent), getSwalInput(templateContent), getSwalStringParams(templateContent, swalStringParams));
          return result;
        };
        const getSwalParams = (templateContent) => {
          const result = {};
          const swalParams = Array.from(templateContent.querySelectorAll("swal-param"));
          swalParams.forEach((param) => {
            showWarningsForAttributes(param, ["name", "value"]);
            const paramName = (
              /** @type {keyof SweetAlertOptions} */
              param.getAttribute("name")
            );
            const value = param.getAttribute("value");
            if (!paramName || !value) {
              return;
            }
            if (paramName in defaultParams && typeof defaultParams[
              /** @type {keyof typeof defaultParams} */
              paramName
            ] === "boolean") {
              result[paramName] = value !== "false";
            } else if (paramName in defaultParams && typeof defaultParams[
              /** @type {keyof typeof defaultParams} */
              paramName
            ] === "object") {
              result[paramName] = JSON.parse(value);
            } else {
              result[paramName] = value;
            }
          });
          return result;
        };
        const getSwalFunctionParams = (templateContent) => {
          const result = {};
          const swalFunctions = Array.from(templateContent.querySelectorAll("swal-function-param"));
          swalFunctions.forEach((param) => {
            const paramName = (
              /** @type {keyof SweetAlertOptions} */
              param.getAttribute("name")
            );
            const value = param.getAttribute("value");
            if (!paramName || !value) {
              return;
            }
            result[paramName] = new Function(`return ${value}`)();
          });
          return result;
        };
        const getSwalButtons = (templateContent) => {
          const result = {};
          const swalButtons = Array.from(templateContent.querySelectorAll("swal-button"));
          swalButtons.forEach((button) => {
            showWarningsForAttributes(button, ["type", "color", "aria-label"]);
            const type = button.getAttribute("type");
            if (!type || !["confirm", "cancel", "deny"].includes(type)) {
              return;
            }
            result[`${type}ButtonText`] = button.innerHTML;
            result[`show${capitalizeFirstLetter(type)}Button`] = true;
            if (button.hasAttribute("color")) {
              const color = button.getAttribute("color");
              if (color !== null) {
                result[`${type}ButtonColor`] = color;
              }
            }
            if (button.hasAttribute("aria-label")) {
              const ariaLabel = button.getAttribute("aria-label");
              if (ariaLabel !== null) {
                result[`${type}ButtonAriaLabel`] = ariaLabel;
              }
            }
          });
          return result;
        };
        const getSwalImage = (templateContent) => {
          const result = {};
          const image = templateContent.querySelector("swal-image");
          if (image) {
            showWarningsForAttributes(image, ["src", "width", "height", "alt"]);
            if (image.hasAttribute("src")) {
              result.imageUrl = image.getAttribute("src") || void 0;
            }
            if (image.hasAttribute("width")) {
              result.imageWidth = image.getAttribute("width") || void 0;
            }
            if (image.hasAttribute("height")) {
              result.imageHeight = image.getAttribute("height") || void 0;
            }
            if (image.hasAttribute("alt")) {
              result.imageAlt = image.getAttribute("alt") || void 0;
            }
          }
          return result;
        };
        const getSwalIcon = (templateContent) => {
          const result = {};
          const icon = templateContent.querySelector("swal-icon");
          if (icon) {
            showWarningsForAttributes(icon, ["type", "color"]);
            if (icon.hasAttribute("type")) {
              result.icon = icon.getAttribute("type");
            }
            if (icon.hasAttribute("color")) {
              result.iconColor = icon.getAttribute("color");
            }
            result.iconHtml = icon.innerHTML;
          }
          return result;
        };
        const getSwalInput = (templateContent) => {
          const result = {};
          const input = templateContent.querySelector("swal-input");
          if (input) {
            showWarningsForAttributes(input, ["type", "label", "placeholder", "value"]);
            result.input = input.getAttribute("type") || "text";
            if (input.hasAttribute("label")) {
              result.inputLabel = input.getAttribute("label");
            }
            if (input.hasAttribute("placeholder")) {
              result.inputPlaceholder = input.getAttribute("placeholder");
            }
            if (input.hasAttribute("value")) {
              result.inputValue = input.getAttribute("value");
            }
          }
          const inputOptions = Array.from(templateContent.querySelectorAll("swal-input-option"));
          if (inputOptions.length) {
            result.inputOptions = {};
            inputOptions.forEach((option) => {
              showWarningsForAttributes(option, ["value"]);
              const optionValue = option.getAttribute("value");
              if (!optionValue) {
                return;
              }
              const optionName = option.innerHTML;
              result.inputOptions[optionValue] = optionName;
            });
          }
          return result;
        };
        const getSwalStringParams = (templateContent, paramNames) => {
          const result = {};
          for (const i in paramNames) {
            const paramName = paramNames[i];
            const tag = templateContent.querySelector(paramName);
            if (tag) {
              showWarningsForAttributes(tag, []);
              result[paramName.replace(/^swal-/, "")] = tag.innerHTML.trim();
            }
          }
          return result;
        };
        const showWarningsForElements = (templateContent) => {
          const allowedElements = swalStringParams.concat(["swal-param", "swal-function-param", "swal-button", "swal-image", "swal-icon", "swal-input", "swal-input-option"]);
          Array.from(templateContent.children).forEach((el) => {
            const tagName = el.tagName.toLowerCase();
            if (!allowedElements.includes(tagName)) {
              warn(`Unrecognized element <${tagName}>`);
            }
          });
        };
        const showWarningsForAttributes = (el, allowedAttributes) => {
          Array.from(el.attributes).forEach((attribute) => {
            if (allowedAttributes.indexOf(attribute.name) === -1) {
              warn([`Unrecognized attribute "${attribute.name}" on <${el.tagName.toLowerCase()}>.`, `${allowedAttributes.length ? `Allowed attributes are: ${allowedAttributes.join(", ")}` : "To set the value, use HTML within the element."}`]);
            }
          });
        };
        const SHOW_CLASS_TIMEOUT = 10;
        const openPopup = (params) => {
          var _globalState$eventEmi, _globalState$eventEmi2;
          const container = getContainer();
          const popup = getPopup();
          if (!container || !popup) {
            return;
          }
          if (typeof params.willOpen === "function") {
            params.willOpen(popup);
          }
          (_globalState$eventEmi = globalState.eventEmitter) === null || _globalState$eventEmi === void 0 || _globalState$eventEmi.emit("willOpen", popup);
          const bodyStyles = window.getComputedStyle(document.body);
          const initialBodyOverflow = bodyStyles.overflowY;
          addClasses(container, popup, params);
          setTimeout(() => {
            setScrollingVisibility(container, popup);
          }, SHOW_CLASS_TIMEOUT);
          if (isModal()) {
            fixScrollContainer(container, params.scrollbarPadding !== void 0 ? params.scrollbarPadding : false, initialBodyOverflow);
            setAriaHidden();
          }
          if (!isToast() && !globalState.previousActiveElement) {
            globalState.previousActiveElement = document.activeElement;
          }
          if (typeof params.didOpen === "function") {
            const didOpen = params.didOpen;
            setTimeout(() => didOpen(popup));
          }
          (_globalState$eventEmi2 = globalState.eventEmitter) === null || _globalState$eventEmi2 === void 0 || _globalState$eventEmi2.emit("didOpen", popup);
        };
        const swalOpenAnimationFinished = (event) => {
          const popup = getPopup();
          if (!popup || event.target !== popup) {
            return;
          }
          const container = getContainer();
          if (!container) {
            return;
          }
          popup.removeEventListener("animationend", swalOpenAnimationFinished);
          popup.removeEventListener("transitionend", swalOpenAnimationFinished);
          container.style.overflowY = "auto";
          removeClass(container, swalClasses["no-transition"]);
        };
        const setScrollingVisibility = (container, popup) => {
          if (hasCssAnimation(popup)) {
            container.style.overflowY = "hidden";
            popup.addEventListener("animationend", swalOpenAnimationFinished);
            popup.addEventListener("transitionend", swalOpenAnimationFinished);
          } else {
            container.style.overflowY = "auto";
          }
        };
        const fixScrollContainer = (container, scrollbarPadding, initialBodyOverflow) => {
          iOSfix();
          if (scrollbarPadding && initialBodyOverflow !== "hidden") {
            replaceScrollbarWithPadding(initialBodyOverflow);
          }
          setTimeout(() => {
            container.scrollTop = 0;
          });
        };
        const addClasses = (container, popup, params) => {
          var _params$showClass;
          if ((_params$showClass = params.showClass) !== null && _params$showClass !== void 0 && _params$showClass.backdrop) {
            addClass(container, params.showClass.backdrop);
          }
          if (params.animation) {
            popup.style.setProperty("opacity", "0", "important");
            show(popup, "grid");
            setTimeout(() => {
              var _params$showClass2;
              if ((_params$showClass2 = params.showClass) !== null && _params$showClass2 !== void 0 && _params$showClass2.popup) {
                addClass(popup, params.showClass.popup);
              }
              popup.style.removeProperty("opacity");
            }, SHOW_CLASS_TIMEOUT);
          } else {
            show(popup, "grid");
          }
          addClass([document.documentElement, document.body], swalClasses.shown);
          if (params.heightAuto && params.backdrop && !params.toast) {
            addClass([document.documentElement, document.body], swalClasses["height-auto"]);
          }
        };
        var defaultInputValidators = {
          /**
           * @param {string} string
           * @param {string} [validationMessage]
           * @returns {Promise<string | void>}
           */
          email: (string, validationMessage) => {
            return /^[a-zA-Z0-9.+_'-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9-]+$/.test(string) ? Promise.resolve() : Promise.resolve(validationMessage || "Invalid email address");
          },
          /**
           * @param {string} string
           * @param {string} [validationMessage]
           * @returns {Promise<string | void>}
           */
          url: (string, validationMessage) => {
            return /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-z]{2,63}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)$/.test(string) ? Promise.resolve() : Promise.resolve(validationMessage || "Invalid URL");
          }
        };
        function setDefaultInputValidators(params) {
          if (params.inputValidator) {
            return;
          }
          if (params.input === "email") {
            params.inputValidator = defaultInputValidators["email"];
          }
          if (params.input === "url") {
            params.inputValidator = defaultInputValidators["url"];
          }
        }
        function validateCustomTargetElement(params) {
          if (!params.target || typeof params.target === "string" && !document.querySelector(params.target) || typeof params.target !== "string" && !params.target.appendChild) {
            warn('Target parameter is not valid, defaulting to "body"');
            params.target = "body";
          }
        }
        function setParameters(params) {
          setDefaultInputValidators(params);
          if (params.showLoaderOnConfirm && !params.preConfirm) {
            warn("showLoaderOnConfirm is set to true, but preConfirm is not defined.\nshowLoaderOnConfirm should be used together with preConfirm, see usage example:\nhttps://sweetalert2.github.io/#ajax-request");
          }
          validateCustomTargetElement(params);
          if (typeof params.title === "string") {
            params.title = params.title.split("\n").join("<br />");
          }
          init(params);
        }
        let currentInstance;
        var _promise = /* @__PURE__ */ new WeakMap();
        class SweetAlert {
          /**
           * @param {...(SweetAlertOptions | string)} args
           * @this {SweetAlert}
           */
          constructor(...args) {
            _classPrivateFieldInitSpec(
              this,
              _promise,
              /** @type {Promise<SweetAlertResult>} */
              Promise.resolve({
                isConfirmed: false,
                isDenied: false,
                isDismissed: true
              })
            );
            if (typeof window === "undefined") {
              return;
            }
            currentInstance = this;
            const outerParams = Object.freeze(this.constructor.argsToParams(args));
            this.params = outerParams;
            this.isAwaitingPromise = false;
            _classPrivateFieldSet2(_promise, this, this._main(currentInstance.params));
          }
          /**
           * @param {any} userParams
           * @param {any} mixinParams
           */
          _main(userParams, mixinParams = {}) {
            showWarningsForParams(Object.assign({}, mixinParams, userParams));
            if (globalState.currentInstance) {
              const swalPromiseResolve = privateMethods.swalPromiseResolve.get(globalState.currentInstance);
              const {
                isAwaitingPromise
              } = globalState.currentInstance;
              globalState.currentInstance._destroy();
              if (!isAwaitingPromise) {
                swalPromiseResolve({
                  isDismissed: true
                });
              }
              if (isModal()) {
                unsetAriaHidden();
              }
            }
            globalState.currentInstance = currentInstance;
            const innerParams = prepareParams(userParams, mixinParams);
            setParameters(innerParams);
            Object.freeze(innerParams);
            if (globalState.timeout) {
              globalState.timeout.stop();
              delete globalState.timeout;
            }
            clearTimeout(globalState.restoreFocusTimeout);
            const domCache = populateDomCache(currentInstance);
            render(currentInstance, innerParams);
            privateProps.innerParams.set(currentInstance, innerParams);
            return swalPromise(currentInstance, domCache, innerParams);
          }
          // `catch` cannot be the name of a module export, so we define our thenable methods here instead
          /**
           * @param {any} onFulfilled
           */
          then(onFulfilled) {
            return _classPrivateFieldGet2(_promise, this).then(onFulfilled);
          }
          /**
           * @param {any} onFinally
           */
          finally(onFinally) {
            return _classPrivateFieldGet2(_promise, this).finally(onFinally);
          }
        }
        const swalPromise = (instance, domCache, innerParams) => {
          return new Promise((resolve, reject) => {
            const dismissWith = (dismiss) => {
              instance.close({
                isDismissed: true,
                dismiss,
                isConfirmed: false,
                isDenied: false
              });
            };
            privateMethods.swalPromiseResolve.set(instance, resolve);
            privateMethods.swalPromiseReject.set(instance, reject);
            domCache.confirmButton.onclick = () => {
              handleConfirmButtonClick(instance);
            };
            domCache.denyButton.onclick = () => {
              handleDenyButtonClick(instance);
            };
            domCache.cancelButton.onclick = () => {
              handleCancelButtonClick(instance, dismissWith);
            };
            domCache.closeButton.onclick = () => {
              dismissWith(DismissReason.close);
            };
            handlePopupClick(innerParams, domCache, dismissWith);
            addKeydownHandler(globalState, innerParams, dismissWith);
            handleInputOptionsAndValue(instance, innerParams);
            openPopup(innerParams);
            setupTimer(globalState, innerParams, dismissWith);
            initFocus(domCache, innerParams);
            setTimeout(() => {
              domCache.container.scrollTop = 0;
            });
          });
        };
        const prepareParams = (userParams, mixinParams) => {
          const templateParams = getTemplateParams(userParams);
          const params = Object.assign({}, defaultParams, mixinParams, templateParams, userParams);
          params.showClass = Object.assign({}, defaultParams.showClass, params.showClass);
          params.hideClass = Object.assign({}, defaultParams.hideClass, params.hideClass);
          if (params.animation === false) {
            params.showClass = {
              backdrop: "swal2-noanimation"
            };
            params.hideClass = {};
          }
          return params;
        };
        const populateDomCache = (instance) => {
          const domCache = (
            /** @type {DomCache} */
            {
              popup: (
                /** @type {HTMLElement} */
                getPopup()
              ),
              container: (
                /** @type {HTMLElement} */
                getContainer()
              ),
              actions: (
                /** @type {HTMLElement} */
                getActions()
              ),
              confirmButton: (
                /** @type {HTMLElement} */
                getConfirmButton()
              ),
              denyButton: (
                /** @type {HTMLElement} */
                getDenyButton()
              ),
              cancelButton: (
                /** @type {HTMLElement} */
                getCancelButton()
              ),
              loader: (
                /** @type {HTMLElement} */
                getLoader()
              ),
              closeButton: (
                /** @type {HTMLElement} */
                getCloseButton()
              ),
              validationMessage: (
                /** @type {HTMLElement} */
                getValidationMessage()
              ),
              progressSteps: (
                /** @type {HTMLElement} */
                getProgressSteps()
              )
            }
          );
          privateProps.domCache.set(instance, domCache);
          return domCache;
        };
        const setupTimer = (globalState2, innerParams, dismissWith) => {
          const timerProgressBar = getTimerProgressBar();
          hide(timerProgressBar);
          if (innerParams.timer) {
            globalState2.timeout = new Timer(() => {
              dismissWith("timer");
              delete globalState2.timeout;
            }, innerParams.timer);
            if (innerParams.timerProgressBar && timerProgressBar) {
              show(timerProgressBar);
              applyCustomClass(timerProgressBar, innerParams, "timerProgressBar");
              setTimeout(() => {
                if (globalState2.timeout && globalState2.timeout.running) {
                  animateTimerProgressBar(
                    /** @type {number} */
                    innerParams.timer
                  );
                }
              });
            }
          }
        };
        const initFocus = (domCache, innerParams) => {
          if (innerParams.toast) {
            return;
          }
          if (!callIfFunction(innerParams.allowEnterKey)) {
            warnAboutDeprecation("allowEnterKey");
            blurActiveElement();
            return;
          }
          if (focusAutofocus(domCache)) {
            return;
          }
          if (focusButton(domCache, innerParams)) {
            return;
          }
          setFocus(-1, 1);
        };
        const focusAutofocus = (domCache) => {
          const autofocusElements = Array.from(domCache.popup.querySelectorAll("[autofocus]"));
          for (const autofocusElement of autofocusElements) {
            if (autofocusElement instanceof HTMLElement && isVisible$1(autofocusElement)) {
              autofocusElement.focus();
              return true;
            }
          }
          return false;
        };
        const focusButton = (domCache, innerParams) => {
          if (innerParams.focusDeny && isVisible$1(domCache.denyButton)) {
            domCache.denyButton.focus();
            return true;
          }
          if (innerParams.focusCancel && isVisible$1(domCache.cancelButton)) {
            domCache.cancelButton.focus();
            return true;
          }
          if (innerParams.focusConfirm && isVisible$1(domCache.confirmButton)) {
            domCache.confirmButton.focus();
            return true;
          }
          return false;
        };
        const blurActiveElement = () => {
          if (document.activeElement instanceof HTMLElement && typeof document.activeElement.blur === "function") {
            document.activeElement.blur();
          }
        };
        SweetAlert.prototype.disableButtons = disableButtons;
        SweetAlert.prototype.enableButtons = enableButtons;
        SweetAlert.prototype.getInput = getInput;
        SweetAlert.prototype.disableInput = disableInput;
        SweetAlert.prototype.enableInput = enableInput;
        SweetAlert.prototype.hideLoading = hideLoading;
        SweetAlert.prototype.disableLoading = hideLoading;
        SweetAlert.prototype.showValidationMessage = showValidationMessage;
        SweetAlert.prototype.resetValidationMessage = resetValidationMessage;
        SweetAlert.prototype.close = close;
        SweetAlert.prototype.closePopup = close;
        SweetAlert.prototype.closeModal = close;
        SweetAlert.prototype.closeToast = close;
        SweetAlert.prototype.rejectPromise = rejectPromise;
        SweetAlert.prototype.update = update;
        SweetAlert.prototype._destroy = _destroy;
        Object.assign(SweetAlert, staticMethods);
        Object.keys(instanceMethods).forEach((key) => {
          SweetAlert[key] = function(...args) {
            if (currentInstance && currentInstance[key]) {
              return currentInstance[key](...args);
            }
            return void 0;
          };
        });
        SweetAlert.DismissReason = DismissReason;
        SweetAlert.version = "11.26.17";
        const Swal2 = SweetAlert;
        Swal2.default = Swal2;
        return Swal2;
      });
      if (typeof exports !== "undefined" && exports.Sweetalert2) {
        exports.swal = exports.sweetAlert = exports.Swal = exports.SweetAlert = exports.Sweetalert2;
      }
      "undefined" != typeof document && function(e, t) {
        var n = e.createElement("style");
        if (e.getElementsByTagName("head")[0].appendChild(n), n.styleSheet) n.styleSheet.disabled || (n.styleSheet.cssText = t);
        else try {
          n.innerHTML = t;
        } catch (e2) {
          n.innerText = t;
        }
      }(document, ':root{--swal2-outline: 0 0 0 3px rgba(100, 150, 200, 0.5);--swal2-container-padding: 0.625em;--swal2-backdrop: rgba(0, 0, 0, 0.4);--swal2-backdrop-transition: background-color 0.15s;--swal2-width: 32em;--swal2-padding: 0 0 1.25em;--swal2-border: none;--swal2-border-radius: 0.3125rem;--swal2-background: white;--swal2-color: #545454;--swal2-show-animation: swal2-show 0.3s;--swal2-hide-animation: swal2-hide 0.15s forwards;--swal2-icon-zoom: 1;--swal2-icon-animations: true;--swal2-title-padding: 0.8em 1em 0;--swal2-html-container-padding: 1em 1.6em 0.3em;--swal2-input-border: 1px solid #d9d9d9;--swal2-input-border-radius: 0.1875em;--swal2-input-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.06), 0 0 0 3px transparent;--swal2-input-background: transparent;--swal2-input-transition: border-color 0.2s, box-shadow 0.2s;--swal2-input-hover-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.06), 0 0 0 3px transparent;--swal2-input-focus-border: 1px solid #b4dbed;--swal2-input-focus-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.06), 0 0 0 3px rgba(100, 150, 200, 0.5);--swal2-progress-step-background: #add8e6;--swal2-validation-message-background: #f0f0f0;--swal2-validation-message-color: #666;--swal2-footer-border-color: #eee;--swal2-footer-background: transparent;--swal2-footer-color: inherit;--swal2-timer-progress-bar-background: rgba(0, 0, 0, 0.3);--swal2-close-button-position: initial;--swal2-close-button-inset: auto;--swal2-close-button-font-size: 2.5em;--swal2-close-button-color: #ccc;--swal2-close-button-transition: color 0.2s, box-shadow 0.2s;--swal2-close-button-outline: initial;--swal2-close-button-box-shadow: inset 0 0 0 3px transparent;--swal2-close-button-focus-box-shadow: inset var(--swal2-outline);--swal2-close-button-hover-transform: none;--swal2-actions-justify-content: center;--swal2-actions-width: auto;--swal2-actions-margin: 1.25em auto 0;--swal2-actions-padding: 0;--swal2-actions-border-radius: 0;--swal2-actions-background: transparent;--swal2-action-button-transition: background-color 0.2s, box-shadow 0.2s;--swal2-action-button-hover: black 10%;--swal2-action-button-active: black 10%;--swal2-confirm-button-box-shadow: none;--swal2-confirm-button-border-radius: 0.25em;--swal2-confirm-button-background-color: #7066e0;--swal2-confirm-button-color: #fff;--swal2-deny-button-box-shadow: none;--swal2-deny-button-border-radius: 0.25em;--swal2-deny-button-background-color: #dc3741;--swal2-deny-button-color: #fff;--swal2-cancel-button-box-shadow: none;--swal2-cancel-button-border-radius: 0.25em;--swal2-cancel-button-background-color: #6e7881;--swal2-cancel-button-color: #fff;--swal2-toast-show-animation: swal2-toast-show 0.5s;--swal2-toast-hide-animation: swal2-toast-hide 0.1s forwards;--swal2-toast-border: none;--swal2-toast-box-shadow: 0 0 1px hsl(0deg 0% 0% / 0.075), 0 1px 2px hsl(0deg 0% 0% / 0.075), 1px 2px 4px hsl(0deg 0% 0% / 0.075), 1px 3px 8px hsl(0deg 0% 0% / 0.075), 2px 4px 16px hsl(0deg 0% 0% / 0.075)}[data-swal2-theme=dark]{--swal2-dark-theme-black: #19191a;--swal2-dark-theme-white: #e1e1e1;--swal2-background: var(--swal2-dark-theme-black);--swal2-color: var(--swal2-dark-theme-white);--swal2-footer-border-color: #555;--swal2-input-background: color-mix(in srgb, var(--swal2-dark-theme-black), var(--swal2-dark-theme-white) 10%);--swal2-validation-message-background: color-mix( in srgb, var(--swal2-dark-theme-black), var(--swal2-dark-theme-white) 10% );--swal2-validation-message-color: var(--swal2-dark-theme-white);--swal2-timer-progress-bar-background: rgba(255, 255, 255, 0.7)}@media(prefers-color-scheme: dark){[data-swal2-theme=auto]{--swal2-dark-theme-black: #19191a;--swal2-dark-theme-white: #e1e1e1;--swal2-background: var(--swal2-dark-theme-black);--swal2-color: var(--swal2-dark-theme-white);--swal2-footer-border-color: #555;--swal2-input-background: color-mix(in srgb, var(--swal2-dark-theme-black), var(--swal2-dark-theme-white) 10%);--swal2-validation-message-background: color-mix( in srgb, var(--swal2-dark-theme-black), var(--swal2-dark-theme-white) 10% );--swal2-validation-message-color: var(--swal2-dark-theme-white);--swal2-timer-progress-bar-background: rgba(255, 255, 255, 0.7)}}body.swal2-shown:not(.swal2-no-backdrop,.swal2-toast-shown){overflow:hidden}body.swal2-height-auto{height:auto !important}body.swal2-no-backdrop .swal2-container{background-color:rgba(0,0,0,0) !important;pointer-events:none}body.swal2-no-backdrop .swal2-container .swal2-popup{pointer-events:all}body.swal2-no-backdrop .swal2-container .swal2-modal{box-shadow:0 0 10px var(--swal2-backdrop)}body.swal2-toast-shown .swal2-container{box-sizing:border-box;width:360px;max-width:100%;background-color:rgba(0,0,0,0);pointer-events:none}body.swal2-toast-shown .swal2-container.swal2-top{inset:0 auto auto 50%;transform:translateX(-50%)}body.swal2-toast-shown .swal2-container.swal2-top-end,body.swal2-toast-shown .swal2-container.swal2-top-right{inset:0 0 auto auto}body.swal2-toast-shown .swal2-container.swal2-top-start,body.swal2-toast-shown .swal2-container.swal2-top-left{inset:0 auto auto 0}body.swal2-toast-shown .swal2-container.swal2-center-start,body.swal2-toast-shown .swal2-container.swal2-center-left{inset:50% auto auto 0;transform:translateY(-50%)}body.swal2-toast-shown .swal2-container.swal2-center{inset:50% auto auto 50%;transform:translate(-50%, -50%)}body.swal2-toast-shown .swal2-container.swal2-center-end,body.swal2-toast-shown .swal2-container.swal2-center-right{inset:50% 0 auto auto;transform:translateY(-50%)}body.swal2-toast-shown .swal2-container.swal2-bottom-start,body.swal2-toast-shown .swal2-container.swal2-bottom-left{inset:auto auto 0 0}body.swal2-toast-shown .swal2-container.swal2-bottom{inset:auto auto 0 50%;transform:translateX(-50%)}body.swal2-toast-shown .swal2-container.swal2-bottom-end,body.swal2-toast-shown .swal2-container.swal2-bottom-right{inset:auto 0 0 auto}@media print{body.swal2-shown:not(.swal2-no-backdrop,.swal2-toast-shown){overflow-y:scroll !important}body.swal2-shown:not(.swal2-no-backdrop,.swal2-toast-shown)>[aria-hidden=true]{display:none}body.swal2-shown:not(.swal2-no-backdrop,.swal2-toast-shown) .swal2-container{position:static !important}}div:where(.swal2-container){display:grid;position:fixed;z-index:1060;inset:0;box-sizing:border-box;grid-template-areas:"top-start     top            top-end" "center-start  center         center-end" "bottom-start  bottom-center  bottom-end";grid-template-rows:minmax(min-content, auto) minmax(min-content, auto) minmax(min-content, auto);height:100%;padding:var(--swal2-container-padding);overflow-x:hidden;transition:var(--swal2-backdrop-transition);-webkit-overflow-scrolling:touch}div:where(.swal2-container).swal2-backdrop-show,div:where(.swal2-container).swal2-noanimation{background:var(--swal2-backdrop)}div:where(.swal2-container).swal2-backdrop-hide{background:rgba(0,0,0,0) !important}div:where(.swal2-container).swal2-top-start,div:where(.swal2-container).swal2-center-start,div:where(.swal2-container).swal2-bottom-start{grid-template-columns:minmax(0, 1fr) auto auto}div:where(.swal2-container).swal2-top,div:where(.swal2-container).swal2-center,div:where(.swal2-container).swal2-bottom{grid-template-columns:auto minmax(0, 1fr) auto}div:where(.swal2-container).swal2-top-end,div:where(.swal2-container).swal2-center-end,div:where(.swal2-container).swal2-bottom-end{grid-template-columns:auto auto minmax(0, 1fr)}div:where(.swal2-container).swal2-top-start>.swal2-popup{align-self:start}div:where(.swal2-container).swal2-top>.swal2-popup{grid-column:2;place-self:start center}div:where(.swal2-container).swal2-top-end>.swal2-popup,div:where(.swal2-container).swal2-top-right>.swal2-popup{grid-column:3;place-self:start end}div:where(.swal2-container).swal2-center-start>.swal2-popup,div:where(.swal2-container).swal2-center-left>.swal2-popup{grid-row:2;align-self:center}div:where(.swal2-container).swal2-center>.swal2-popup{grid-column:2;grid-row:2;place-self:center center}div:where(.swal2-container).swal2-center-end>.swal2-popup,div:where(.swal2-container).swal2-center-right>.swal2-popup{grid-column:3;grid-row:2;place-self:center end}div:where(.swal2-container).swal2-bottom-start>.swal2-popup,div:where(.swal2-container).swal2-bottom-left>.swal2-popup{grid-column:1;grid-row:3;align-self:end}div:where(.swal2-container).swal2-bottom>.swal2-popup{grid-column:2;grid-row:3;place-self:end center}div:where(.swal2-container).swal2-bottom-end>.swal2-popup,div:where(.swal2-container).swal2-bottom-right>.swal2-popup{grid-column:3;grid-row:3;place-self:end end}div:where(.swal2-container).swal2-grow-row>.swal2-popup,div:where(.swal2-container).swal2-grow-fullscreen>.swal2-popup{grid-column:1/4;width:100%}div:where(.swal2-container).swal2-grow-column>.swal2-popup,div:where(.swal2-container).swal2-grow-fullscreen>.swal2-popup{grid-row:1/4;align-self:stretch}div:where(.swal2-container).swal2-no-transition{transition:none !important}div:where(.swal2-container)[popover]{width:auto;border:0}div:where(.swal2-container) div:where(.swal2-popup){display:none;position:relative;box-sizing:border-box;grid-template-columns:minmax(0, 100%);width:var(--swal2-width);max-width:100%;padding:var(--swal2-padding);border:var(--swal2-border);border-radius:var(--swal2-border-radius);background:var(--swal2-background);color:var(--swal2-color);font-family:inherit;font-size:1rem;container-name:swal2-popup}div:where(.swal2-container) div:where(.swal2-popup):focus{outline:none}div:where(.swal2-container) div:where(.swal2-popup).swal2-loading{overflow-y:hidden}div:where(.swal2-container) div:where(.swal2-popup).swal2-draggable{cursor:grab}div:where(.swal2-container) div:where(.swal2-popup).swal2-draggable div:where(.swal2-icon){cursor:grab}div:where(.swal2-container) div:where(.swal2-popup).swal2-dragging{cursor:grabbing}div:where(.swal2-container) div:where(.swal2-popup).swal2-dragging div:where(.swal2-icon){cursor:grabbing}div:where(.swal2-container) h2:where(.swal2-title){position:relative;max-width:100%;margin:0;padding:var(--swal2-title-padding);color:inherit;font-size:1.875em;font-weight:600;text-align:center;text-transform:none;overflow-wrap:break-word;cursor:initial}div:where(.swal2-container) div:where(.swal2-actions){display:flex;z-index:1;box-sizing:border-box;flex-wrap:wrap;align-items:center;justify-content:var(--swal2-actions-justify-content);width:var(--swal2-actions-width);margin:var(--swal2-actions-margin);padding:var(--swal2-actions-padding);border-radius:var(--swal2-actions-border-radius);background:var(--swal2-actions-background)}div:where(.swal2-container) div:where(.swal2-loader){display:none;align-items:center;justify-content:center;width:2.2em;height:2.2em;margin:0 1.875em;animation:swal2-rotate-loading 1.5s linear 0s infinite normal;border-width:.25em;border-style:solid;border-radius:100%;border-color:#2778c4 rgba(0,0,0,0) #2778c4 rgba(0,0,0,0)}div:where(.swal2-container) button:where(.swal2-styled){margin:.3125em;padding:.625em 1.1em;transition:var(--swal2-action-button-transition);border:none;box-shadow:0 0 0 3px rgba(0,0,0,0);font-weight:500}div:where(.swal2-container) button:where(.swal2-styled):not([disabled]){cursor:pointer}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-confirm){border-radius:var(--swal2-confirm-button-border-radius);background:initial;background-color:var(--swal2-confirm-button-background-color);box-shadow:var(--swal2-confirm-button-box-shadow);color:var(--swal2-confirm-button-color);font-size:1em}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-confirm):hover{background-color:color-mix(in srgb, var(--swal2-confirm-button-background-color), var(--swal2-action-button-hover))}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-confirm):active{background-color:color-mix(in srgb, var(--swal2-confirm-button-background-color), var(--swal2-action-button-active))}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-deny){border-radius:var(--swal2-deny-button-border-radius);background:initial;background-color:var(--swal2-deny-button-background-color);box-shadow:var(--swal2-deny-button-box-shadow);color:var(--swal2-deny-button-color);font-size:1em}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-deny):hover{background-color:color-mix(in srgb, var(--swal2-deny-button-background-color), var(--swal2-action-button-hover))}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-deny):active{background-color:color-mix(in srgb, var(--swal2-deny-button-background-color), var(--swal2-action-button-active))}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-cancel){border-radius:var(--swal2-cancel-button-border-radius);background:initial;background-color:var(--swal2-cancel-button-background-color);box-shadow:var(--swal2-cancel-button-box-shadow);color:var(--swal2-cancel-button-color);font-size:1em}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-cancel):hover{background-color:color-mix(in srgb, var(--swal2-cancel-button-background-color), var(--swal2-action-button-hover))}div:where(.swal2-container) button:where(.swal2-styled):where(.swal2-cancel):active{background-color:color-mix(in srgb, var(--swal2-cancel-button-background-color), var(--swal2-action-button-active))}div:where(.swal2-container) button:where(.swal2-styled):focus-visible{outline:none;box-shadow:var(--swal2-action-button-focus-box-shadow)}div:where(.swal2-container) button:where(.swal2-styled)[disabled]:not(.swal2-loading){opacity:.4}div:where(.swal2-container) button:where(.swal2-styled)::-moz-focus-inner{border:0}div:where(.swal2-container) div:where(.swal2-footer){margin:1em 0 0;padding:1em 1em 0;border-top:1px solid var(--swal2-footer-border-color);background:var(--swal2-footer-background);color:var(--swal2-footer-color);font-size:1em;text-align:center;cursor:initial}div:where(.swal2-container) .swal2-timer-progress-bar-container{position:absolute;right:0;bottom:0;left:0;grid-column:auto !important;overflow:hidden;border-bottom-right-radius:var(--swal2-border-radius);border-bottom-left-radius:var(--swal2-border-radius)}div:where(.swal2-container) div:where(.swal2-timer-progress-bar){width:100%;height:.25em;background:var(--swal2-timer-progress-bar-background)}div:where(.swal2-container) img:where(.swal2-image){max-width:100%;margin:2em auto 1em;cursor:initial}div:where(.swal2-container) button:where(.swal2-close){position:var(--swal2-close-button-position);inset:var(--swal2-close-button-inset);z-index:2;align-items:center;justify-content:center;width:1.2em;height:1.2em;margin-top:0;margin-right:0;margin-bottom:-1.2em;padding:0;overflow:hidden;transition:var(--swal2-close-button-transition);border:none;border-radius:var(--swal2-border-radius);outline:var(--swal2-close-button-outline);background:rgba(0,0,0,0);color:var(--swal2-close-button-color);font-family:monospace;font-size:var(--swal2-close-button-font-size);cursor:pointer;justify-self:end}div:where(.swal2-container) button:where(.swal2-close):hover{transform:var(--swal2-close-button-hover-transform);background:rgba(0,0,0,0);color:#f27474}div:where(.swal2-container) button:where(.swal2-close):focus-visible{outline:none;box-shadow:var(--swal2-close-button-focus-box-shadow)}div:where(.swal2-container) button:where(.swal2-close)::-moz-focus-inner{border:0}div:where(.swal2-container) div:where(.swal2-html-container){z-index:1;justify-content:center;margin:0;padding:var(--swal2-html-container-padding);overflow:auto;color:inherit;font-size:1.125em;font-weight:normal;line-height:normal;text-align:center;overflow-wrap:break-word;word-break:break-word;cursor:initial}div:where(.swal2-container) input:where(.swal2-input),div:where(.swal2-container) input:where(.swal2-file),div:where(.swal2-container) textarea:where(.swal2-textarea),div:where(.swal2-container) select:where(.swal2-select),div:where(.swal2-container) div:where(.swal2-radio),div:where(.swal2-container) label:where(.swal2-checkbox){margin:1em 2em 3px}div:where(.swal2-container) input:where(.swal2-input),div:where(.swal2-container) input:where(.swal2-file),div:where(.swal2-container) textarea:where(.swal2-textarea){box-sizing:border-box;width:auto;transition:var(--swal2-input-transition);border:var(--swal2-input-border);border-radius:var(--swal2-input-border-radius);background:var(--swal2-input-background);box-shadow:var(--swal2-input-box-shadow);color:inherit;font-size:1.125em}div:where(.swal2-container) input:where(.swal2-input).swal2-inputerror,div:where(.swal2-container) input:where(.swal2-file).swal2-inputerror,div:where(.swal2-container) textarea:where(.swal2-textarea).swal2-inputerror{border-color:#f27474 !important;box-shadow:0 0 2px #f27474 !important}div:where(.swal2-container) input:where(.swal2-input):hover,div:where(.swal2-container) input:where(.swal2-file):hover,div:where(.swal2-container) textarea:where(.swal2-textarea):hover{box-shadow:var(--swal2-input-hover-box-shadow)}div:where(.swal2-container) input:where(.swal2-input):focus,div:where(.swal2-container) input:where(.swal2-file):focus,div:where(.swal2-container) textarea:where(.swal2-textarea):focus{border:var(--swal2-input-focus-border);outline:none;box-shadow:var(--swal2-input-focus-box-shadow)}div:where(.swal2-container) input:where(.swal2-input)::placeholder,div:where(.swal2-container) input:where(.swal2-file)::placeholder,div:where(.swal2-container) textarea:where(.swal2-textarea)::placeholder{color:#ccc}div:where(.swal2-container) .swal2-range{margin:1em 2em 3px;background:var(--swal2-background)}div:where(.swal2-container) .swal2-range input{width:80%}div:where(.swal2-container) .swal2-range output{width:20%;color:inherit;font-weight:600;text-align:center}div:where(.swal2-container) .swal2-range input,div:where(.swal2-container) .swal2-range output{height:2.625em;padding:0;font-size:1.125em;line-height:2.625em}div:where(.swal2-container) .swal2-input{height:2.625em;padding:0 .75em}div:where(.swal2-container) .swal2-file{width:75%;margin-right:auto;margin-left:auto;background:var(--swal2-input-background);font-size:1.125em}div:where(.swal2-container) .swal2-textarea{height:6.75em;padding:.75em}div:where(.swal2-container) .swal2-select{min-width:50%;max-width:100%;padding:.375em .625em;background:var(--swal2-input-background);color:inherit;font-size:1.125em}div:where(.swal2-container) .swal2-radio,div:where(.swal2-container) .swal2-checkbox{align-items:center;justify-content:center;background:var(--swal2-background);color:inherit}div:where(.swal2-container) .swal2-radio label,div:where(.swal2-container) .swal2-checkbox label{margin:0 .6em;font-size:1.125em}div:where(.swal2-container) .swal2-radio input,div:where(.swal2-container) .swal2-checkbox input{flex-shrink:0;margin:0 .4em}div:where(.swal2-container) label:where(.swal2-input-label){display:flex;justify-content:center;margin:1em auto 0}div:where(.swal2-container) div:where(.swal2-validation-message){align-items:center;justify-content:center;margin:1em 0 0;padding:.625em;overflow:hidden;background:var(--swal2-validation-message-background);color:var(--swal2-validation-message-color);font-size:1em;font-weight:300}div:where(.swal2-container) div:where(.swal2-validation-message)::before{content:"!";display:inline-block;width:1.5em;min-width:1.5em;height:1.5em;margin:0 .625em;border-radius:50%;background-color:#f27474;color:#fff;font-weight:600;line-height:1.5em;text-align:center}div:where(.swal2-container) .swal2-progress-steps{flex-wrap:wrap;align-items:center;max-width:100%;margin:1.25em auto;padding:0;background:rgba(0,0,0,0);font-weight:600}div:where(.swal2-container) .swal2-progress-steps li{display:inline-block;position:relative}div:where(.swal2-container) .swal2-progress-steps .swal2-progress-step{z-index:20;flex-shrink:0;width:2em;height:2em;border-radius:2em;background:#2778c4;color:#fff;line-height:2em;text-align:center}div:where(.swal2-container) .swal2-progress-steps .swal2-progress-step.swal2-active-progress-step{background:#2778c4}div:where(.swal2-container) .swal2-progress-steps .swal2-progress-step.swal2-active-progress-step~.swal2-progress-step{background:var(--swal2-progress-step-background);color:#fff}div:where(.swal2-container) .swal2-progress-steps .swal2-progress-step.swal2-active-progress-step~.swal2-progress-step-line{background:var(--swal2-progress-step-background)}div:where(.swal2-container) .swal2-progress-steps .swal2-progress-step-line{z-index:10;flex-shrink:0;width:2.5em;height:.4em;margin:0 -1px;background:#2778c4}div:where(.swal2-icon){position:relative;box-sizing:content-box;justify-content:center;width:5em;height:5em;margin:2.5em auto .6em;zoom:var(--swal2-icon-zoom);border:.25em solid rgba(0,0,0,0);border-radius:50%;border-color:#000;font-family:inherit;line-height:5em;cursor:default;user-select:none}div:where(.swal2-icon) .swal2-icon-content{display:flex;align-items:center;font-size:3.75em}div:where(.swal2-icon).swal2-error{border-color:#f27474;color:#f27474}div:where(.swal2-icon).swal2-error .swal2-x-mark{position:relative;flex-grow:1}div:where(.swal2-icon).swal2-error [class^=swal2-x-mark-line]{display:block;position:absolute;top:2.3125em;width:2.9375em;height:.3125em;border-radius:.125em;background-color:#f27474}div:where(.swal2-icon).swal2-error [class^=swal2-x-mark-line][class$=left]{left:1.0625em;transform:rotate(45deg)}div:where(.swal2-icon).swal2-error [class^=swal2-x-mark-line][class$=right]{right:1em;transform:rotate(-45deg)}@container swal2-popup style(--swal2-icon-animations:true){div:where(.swal2-icon).swal2-error.swal2-icon-show{animation:swal2-animate-error-icon .5s}div:where(.swal2-icon).swal2-error.swal2-icon-show .swal2-x-mark{animation:swal2-animate-error-x-mark .5s}}div:where(.swal2-icon).swal2-warning{border-color:#f8bb86;color:#f8bb86}@container swal2-popup style(--swal2-icon-animations:true){div:where(.swal2-icon).swal2-warning.swal2-icon-show{animation:swal2-animate-error-icon .5s}div:where(.swal2-icon).swal2-warning.swal2-icon-show .swal2-icon-content{animation:swal2-animate-i-mark .5s}}div:where(.swal2-icon).swal2-info{border-color:#3fc3ee;color:#3fc3ee}@container swal2-popup style(--swal2-icon-animations:true){div:where(.swal2-icon).swal2-info.swal2-icon-show{animation:swal2-animate-error-icon .5s}div:where(.swal2-icon).swal2-info.swal2-icon-show .swal2-icon-content{animation:swal2-animate-i-mark .8s}}div:where(.swal2-icon).swal2-question{border-color:#87adbd;color:#87adbd}@container swal2-popup style(--swal2-icon-animations:true){div:where(.swal2-icon).swal2-question.swal2-icon-show{animation:swal2-animate-error-icon .5s}div:where(.swal2-icon).swal2-question.swal2-icon-show .swal2-icon-content{animation:swal2-animate-question-mark .8s}}div:where(.swal2-icon).swal2-success{border-color:#a5dc86;color:#a5dc86}div:where(.swal2-icon).swal2-success [class^=swal2-success-circular-line]{position:absolute;width:3.75em;height:7.5em;border-radius:50%}div:where(.swal2-icon).swal2-success [class^=swal2-success-circular-line][class$=left]{top:-0.4375em;left:-2.0635em;transform:rotate(-45deg);transform-origin:3.75em 3.75em;border-radius:7.5em 0 0 7.5em}div:where(.swal2-icon).swal2-success [class^=swal2-success-circular-line][class$=right]{top:-0.6875em;left:1.875em;transform:rotate(-45deg);transform-origin:0 3.75em;border-radius:0 7.5em 7.5em 0}div:where(.swal2-icon).swal2-success .swal2-success-ring{position:absolute;z-index:2;top:-0.25em;left:-0.25em;box-sizing:content-box;width:100%;height:100%;border:.25em solid rgba(165,220,134,.3);border-radius:50%}div:where(.swal2-icon).swal2-success .swal2-success-fix{position:absolute;z-index:1;top:.5em;left:1.625em;width:.4375em;height:5.625em;transform:rotate(-45deg)}div:where(.swal2-icon).swal2-success [class^=swal2-success-line]{display:block;position:absolute;z-index:2;height:.3125em;border-radius:.125em;background-color:#a5dc86}div:where(.swal2-icon).swal2-success [class^=swal2-success-line][class$=tip]{top:2.875em;left:.8125em;width:1.5625em;transform:rotate(45deg)}div:where(.swal2-icon).swal2-success [class^=swal2-success-line][class$=long]{top:2.375em;right:.5em;width:2.9375em;transform:rotate(-45deg)}@container swal2-popup style(--swal2-icon-animations:true){div:where(.swal2-icon).swal2-success.swal2-icon-show .swal2-success-line-tip{animation:swal2-animate-success-line-tip .75s}div:where(.swal2-icon).swal2-success.swal2-icon-show .swal2-success-line-long{animation:swal2-animate-success-line-long .75s}div:where(.swal2-icon).swal2-success.swal2-icon-show .swal2-success-circular-line-right{animation:swal2-rotate-success-circular-line 4.25s ease-in}}[class^=swal2]{-webkit-tap-highlight-color:rgba(0,0,0,0)}.swal2-show{animation:var(--swal2-show-animation)}.swal2-hide{animation:var(--swal2-hide-animation)}.swal2-noanimation{transition:none}.swal2-scrollbar-measure{position:absolute;top:-9999px;width:50px;height:50px;overflow:scroll}.swal2-rtl .swal2-close{margin-right:initial;margin-left:0}.swal2-rtl .swal2-timer-progress-bar{right:0;left:auto}.swal2-toast{box-sizing:border-box;grid-column:1/4 !important;grid-row:1/4 !important;grid-template-columns:min-content auto min-content;padding:1em;overflow-y:hidden;border:var(--swal2-toast-border);background:var(--swal2-background);box-shadow:var(--swal2-toast-box-shadow);pointer-events:all}.swal2-toast>*{grid-column:2}.swal2-toast h2:where(.swal2-title){margin:.5em 1em;padding:0;font-size:1em;text-align:initial}.swal2-toast .swal2-loading{justify-content:center}.swal2-toast input:where(.swal2-input){height:2em;margin:.5em;font-size:1em}.swal2-toast .swal2-validation-message{font-size:1em}.swal2-toast div:where(.swal2-footer){margin:.5em 0 0;padding:.5em 0 0;font-size:.8em}.swal2-toast button:where(.swal2-close){grid-column:3/3;grid-row:1/99;align-self:center;width:.8em;height:.8em;margin:0;font-size:2em}.swal2-toast div:where(.swal2-html-container){margin:.5em 1em;padding:0;overflow:initial;font-size:1em;text-align:initial}.swal2-toast div:where(.swal2-html-container):empty{padding:0}.swal2-toast .swal2-loader{grid-column:1;grid-row:1/99;align-self:center;width:2em;height:2em;margin:.25em}.swal2-toast .swal2-icon{grid-column:1;grid-row:1/99;align-self:center;width:2em;min-width:2em;height:2em;margin:0 .5em 0 0}.swal2-toast .swal2-icon .swal2-icon-content{display:flex;align-items:center;font-size:1.8em;font-weight:bold}.swal2-toast .swal2-icon.swal2-success .swal2-success-ring{width:2em;height:2em}.swal2-toast .swal2-icon.swal2-error [class^=swal2-x-mark-line]{top:.875em;width:1.375em}.swal2-toast .swal2-icon.swal2-error [class^=swal2-x-mark-line][class$=left]{left:.3125em}.swal2-toast .swal2-icon.swal2-error [class^=swal2-x-mark-line][class$=right]{right:.3125em}.swal2-toast div:where(.swal2-actions){justify-content:flex-start;height:auto;margin:0;margin-top:.5em;padding:0 .5em}.swal2-toast button:where(.swal2-styled){margin:.25em .5em;padding:.4em .6em;font-size:1em}.swal2-toast .swal2-success{border-color:#a5dc86}.swal2-toast .swal2-success [class^=swal2-success-circular-line]{position:absolute;width:1.6em;height:3em;border-radius:50%}.swal2-toast .swal2-success [class^=swal2-success-circular-line][class$=left]{top:-0.8em;left:-0.5em;transform:rotate(-45deg);transform-origin:2em 2em;border-radius:4em 0 0 4em}.swal2-toast .swal2-success [class^=swal2-success-circular-line][class$=right]{top:-0.25em;left:.9375em;transform-origin:0 1.5em;border-radius:0 4em 4em 0}.swal2-toast .swal2-success .swal2-success-ring{width:2em;height:2em}.swal2-toast .swal2-success .swal2-success-fix{top:0;left:.4375em;width:.4375em;height:2.6875em}.swal2-toast .swal2-success [class^=swal2-success-line]{height:.3125em}.swal2-toast .swal2-success [class^=swal2-success-line][class$=tip]{top:1.125em;left:.1875em;width:.75em}.swal2-toast .swal2-success [class^=swal2-success-line][class$=long]{top:.9375em;right:.1875em;width:1.375em}@container swal2-popup style(--swal2-icon-animations:true){.swal2-toast .swal2-success.swal2-icon-show .swal2-success-line-tip{animation:swal2-toast-animate-success-line-tip .75s}.swal2-toast .swal2-success.swal2-icon-show .swal2-success-line-long{animation:swal2-toast-animate-success-line-long .75s}}.swal2-toast.swal2-show{animation:var(--swal2-toast-show-animation)}.swal2-toast.swal2-hide{animation:var(--swal2-toast-hide-animation)}@keyframes swal2-show{0%{transform:translate3d(0, -50px, 0) scale(0.9);opacity:0}100%{transform:translate3d(0, 0, 0) scale(1);opacity:1}}@keyframes swal2-hide{0%{transform:translate3d(0, 0, 0) scale(1);opacity:1}100%{transform:translate3d(0, -50px, 0) scale(0.9);opacity:0}}@keyframes swal2-animate-success-line-tip{0%{top:1.1875em;left:.0625em;width:0}54%{top:1.0625em;left:.125em;width:0}70%{top:2.1875em;left:-0.375em;width:3.125em}84%{top:3em;left:1.3125em;width:1.0625em}100%{top:2.8125em;left:.8125em;width:1.5625em}}@keyframes swal2-animate-success-line-long{0%{top:3.375em;right:2.875em;width:0}65%{top:3.375em;right:2.875em;width:0}84%{top:2.1875em;right:0;width:3.4375em}100%{top:2.375em;right:.5em;width:2.9375em}}@keyframes swal2-rotate-success-circular-line{0%{transform:rotate(-45deg)}5%{transform:rotate(-45deg)}12%{transform:rotate(-405deg)}100%{transform:rotate(-405deg)}}@keyframes swal2-animate-error-x-mark{0%{margin-top:1.625em;transform:scale(0.4);opacity:0}50%{margin-top:1.625em;transform:scale(0.4);opacity:0}80%{margin-top:-0.375em;transform:scale(1.15)}100%{margin-top:0;transform:scale(1);opacity:1}}@keyframes swal2-animate-error-icon{0%{transform:rotateX(100deg);opacity:0}100%{transform:rotateX(0deg);opacity:1}}@keyframes swal2-rotate-loading{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}@keyframes swal2-animate-question-mark{0%{transform:rotateY(-360deg)}100%{transform:rotateY(0)}}@keyframes swal2-animate-i-mark{0%{transform:rotateZ(45deg);opacity:0}25%{transform:rotateZ(-25deg);opacity:.4}50%{transform:rotateZ(15deg);opacity:.8}75%{transform:rotateZ(-5deg);opacity:1}100%{transform:rotateX(0);opacity:1}}@keyframes swal2-toast-show{0%{transform:translateY(-0.625em) rotateZ(2deg)}33%{transform:translateY(0) rotateZ(-2deg)}66%{transform:translateY(0.3125em) rotateZ(2deg)}100%{transform:translateY(0) rotateZ(0deg)}}@keyframes swal2-toast-hide{100%{transform:rotateZ(1deg);opacity:0}}@keyframes swal2-toast-animate-success-line-tip{0%{top:.5625em;left:.0625em;width:0}54%{top:.125em;left:.125em;width:0}70%{top:.625em;left:-0.25em;width:1.625em}84%{top:1.0625em;left:.75em;width:.5em}100%{top:1.125em;left:.1875em;width:.75em}}@keyframes swal2-toast-animate-success-line-long{0%{top:1.625em;right:1.375em;width:0}65%{top:1.25em;right:.9375em;width:0}84%{top:.9375em;right:0;width:1.125em}100%{top:.9375em;right:.1875em;width:1.375em}}');
    }
  });

  // src/pages/chat/AITravelChat.jsx
  var import_react13 = __toESM(require_react(), 1);
  var import_sweetalert2 = __toESM(require_sweetalert2_all(), 1);

  // src/components/common/AppHeader.jsx
  var import_react5 = __toESM(require_react(), 1);

  // src/components/common/NotificationPanel.jsx
  var import_react2 = __toESM(require_react(), 1);

  // src/context/ThemeContext.jsx
  var import_react = __toESM(require_react(), 1);
  var ThemeContext = (0, import_react.createContext)({ theme: "light" });
  function useTheme() {
    const ctx = (0, import_react.useContext)(ThemeContext);
    return ctx?.theme ?? "light";
  }

  // src/components/common/NotificationPanel.jsx
  function getRelativeTime(isoString) {
    if (!isoString) return "\u0E40\u0E21\u0E37\u0E48\u0E2D\u0E2A\u0E31\u0E01\u0E04\u0E23\u0E39\u0E48";
    try {
      let normalized = String(isoString).trim();
      if (normalized && !/[Zz]|[+-]\d{2}:?\d{2}$/.test(normalized)) {
        normalized = normalized + "Z";
      }
      const date = new Date(normalized);
      const diffMs = Date.now() - date.getTime();
      if (isNaN(diffMs) || diffMs < 0) return "\u0E40\u0E21\u0E37\u0E48\u0E2D\u0E2A\u0E31\u0E01\u0E04\u0E23\u0E39\u0E48";
      const diffSec = Math.floor(diffMs / 1e3);
      const diffMins = Math.floor(diffMs / 6e4);
      const diffHours = Math.floor(diffMs / 36e5);
      const diffDays = Math.floor(diffMs / 864e5);
      if (diffSec < 10) return "\u0E40\u0E21\u0E37\u0E48\u0E2D\u0E2A\u0E31\u0E01\u0E04\u0E23\u0E39\u0E48";
      if (diffSec < 60) return `${diffSec} \u0E27\u0E34\u0E19\u0E32\u0E17\u0E35\u0E17\u0E35\u0E48\u0E41\u0E25\u0E49\u0E27`;
      if (diffMins < 60) return `${diffMins} \u0E19\u0E32\u0E17\u0E35\u0E17\u0E35\u0E48\u0E41\u0E25\u0E49\u0E27`;
      if (diffHours < 24) return `${diffHours} \u0E0A\u0E31\u0E48\u0E27\u0E42\u0E21\u0E07\u0E17\u0E35\u0E48\u0E41\u0E25\u0E49\u0E27`;
      if (diffDays === 1) return "\u0E40\u0E21\u0E37\u0E48\u0E2D\u0E27\u0E32\u0E19";
      if (diffDays < 7) return `${diffDays} \u0E27\u0E31\u0E19\u0E17\u0E35\u0E48\u0E41\u0E25\u0E49\u0E27`;
      return date.toLocaleDateString("th-TH", { year: "numeric", month: "short", day: "numeric" });
    } catch {
      return "\u0E40\u0E21\u0E37\u0E48\u0E2D\u0E2A\u0E31\u0E01\u0E04\u0E23\u0E39\u0E48";
    }
  }
  var TYPE_CONFIG = {
    // Booking
    booking_created: { icon: "\u{1F3AB}", color: "blue", label: "\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07" },
    booking_cancelled: { icon: "\u274C", color: "red", label: "\u0E22\u0E01\u0E40\u0E25\u0E34\u0E01\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07" },
    booking_updated: { icon: "\u270F\uFE0F", color: "blue", label: "\u0E2D\u0E31\u0E1B\u0E40\u0E14\u0E15\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07" },
    trip_change: { icon: "\u270F\uFE0F", color: "blue", label: "\u0E2D\u0E31\u0E1B\u0E40\u0E14\u0E15\u0E17\u0E23\u0E34\u0E1B" },
    trip_edited: { icon: "\u270F\uFE0F", color: "green", label: "\u0E41\u0E01\u0E49\u0E44\u0E02\u0E17\u0E23\u0E34\u0E1B" },
    // Payment
    payment_status: { icon: "\u{1F4B3}", color: "green", label: "\u0E01\u0E32\u0E23\u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19" },
    payment_success: { icon: "\u2705", color: "green", label: "\u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08" },
    payment_failed: { icon: "\u26A0\uFE0F", color: "red", label: "\u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E25\u0E49\u0E21\u0E40\u0E2B\u0E25\u0E27" },
    // Flight alerts
    flight_delayed: { icon: "\u23F0", color: "orange", label: "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E25\u0E48\u0E32\u0E0A\u0E49\u0E32" },
    flight_cancelled: { icon: "\u{1F6AB}", color: "red", label: "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E16\u0E39\u0E01\u0E22\u0E01\u0E40\u0E25\u0E34\u0E01" },
    flight_rescheduled: { icon: "\u{1F504}", color: "orange", label: "\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E40\u0E27\u0E25\u0E32\u0E1A\u0E34\u0E19" },
    trip_alert: { icon: "\u26A0\uFE0F", color: "orange", label: "\u0E41\u0E08\u0E49\u0E07\u0E40\u0E15\u0E37\u0E2D\u0E19\u0E17\u0E23\u0E34\u0E1B" },
    // Check-in
    checkin_reminder_flight: { icon: "\u2708\uFE0F", color: "teal", label: "\u0E40\u0E0A\u0E47\u0E04\u0E2D\u0E34\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07\u0E1A\u0E34\u0E19" },
    checkin_reminder_hotel: { icon: "\u{1F3E8}", color: "teal", label: "\u0E40\u0E0A\u0E47\u0E04\u0E2D\u0E34\u0E19\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21" },
    // Account
    account_email_changed: { icon: "\u{1F4E7}", color: "purple", label: "\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E2D\u0E35\u0E40\u0E21\u0E25" },
    account_password_changed: { icon: "\u{1F512}", color: "purple", label: "\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E23\u0E2B\u0E31\u0E2A\u0E1C\u0E48\u0E32\u0E19" },
    account_card_added: { icon: "\u{1F4B3}", color: "green", label: "\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E1A\u0E31\u0E15\u0E23" },
    account_card_removed: { icon: "\u{1F5D1}\uFE0F", color: "gray", label: "\u0E25\u0E1A\u0E1A\u0E31\u0E15\u0E23" },
    account_cotraveler_added: { icon: "\u{1F465}", color: "blue", label: "\u0E1C\u0E39\u0E49\u0E08\u0E2D\u0E07\u0E23\u0E48\u0E27\u0E21" },
    account_profile_updated: { icon: "\u{1F464}", color: "purple", label: "\u0E2D\u0E31\u0E1B\u0E40\u0E14\u0E15\u0E42\u0E1B\u0E23\u0E44\u0E1F\u0E25\u0E4C" }
  };
  function getTypeConfig(type) {
    return TYPE_CONFIG[type] || { icon: "\u{1F514}", color: "gray", label: "\u0E41\u0E08\u0E49\u0E07\u0E40\u0E15\u0E37\u0E2D\u0E19" };
  }
  function NotificationPanel({
    isOpen,
    onClose,
    notificationCount = 0,
    notifications = [],
    position = { right: 0, top: 0 },
    onNavigateToBookings = null,
    onMarkAsRead = null,
    onClearAll = null
  }) {
    const theme = useTheme();
    const [localNotifications, setLocalNotifications] = (0, import_react2.useState)(notifications);
    const [markingIds, setMarkingIds] = (0, import_react2.useState)(/* @__PURE__ */ new Set());
    const [, setTick] = (0, import_react2.useState)(0);
    (0, import_react2.useEffect)(() => {
      if (!isOpen) return;
      const timer = setInterval(() => setTick((t) => t + 1), 3e4);
      return () => clearInterval(timer);
    }, [isOpen]);
    import_react2.default.useEffect(() => {
      setLocalNotifications(notifications);
    }, [notifications]);
    const handleMarkAsRead = (id) => {
      setMarkingIds((prev) => new Set(prev).add(id));
      if (onMarkAsRead) onMarkAsRead(id);
      setTimeout(() => {
        setLocalNotifications(
          (prev) => prev.map((notif) => notif.id === id ? { ...notif, isRead: true } : notif)
        );
        setMarkingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }, 250);
    };
    const handleClearAll = () => {
      setLocalNotifications((prev) => prev.map((notif) => ({ ...notif, isRead: true })));
      if (onClearAll) onClearAll();
    };
    const newNotifications = localNotifications.filter((n) => !n.isRead);
    const previousNotifications = localNotifications.filter((n) => n.isRead);
    if (!isOpen) return null;
    const renderNotifItem = (notification, isNew) => {
      const cfg = getTypeConfig(notification.type);
      return /* @__PURE__ */ import_react2.default.createElement(
        "div",
        {
          key: notification.id,
          className: `notification-item ${isNew ? "new" : "previous"} notif-color-${cfg.color}${markingIds.has(notification.id) ? " marking-read" : ""}`,
          onClick: () => {
            if (!notification.isRead) handleMarkAsRead(notification.id);
            if (notification.bookingId) {
              if (onNavigateToBookings) onNavigateToBookings();
              else if (window.location.pathname !== "/bookings") window.location.href = "/bookings";
              onClose();
            }
          },
          style: { cursor: "pointer" }
        },
        /* @__PURE__ */ import_react2.default.createElement("div", { className: `notification-icon-wrap notif-icon-${cfg.color}` }, /* @__PURE__ */ import_react2.default.createElement("span", { className: "notif-type-icon" }, cfg.icon)),
        /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-content" }, /* @__PURE__ */ import_react2.default.createElement("div", { className: "notif-type-label" }, notification.title || cfg.label), /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-text" }, notification.message), /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-time" }, /* @__PURE__ */ import_react2.default.createElement("span", { className: "time-icon" }, "\u{1F550}"), getRelativeTime(notification.created_at))),
        isNew && /* @__PURE__ */ import_react2.default.createElement("div", { className: "notif-unread-dot" })
      );
    };
    return /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-panel-overlay", onClick: onClose }, /* @__PURE__ */ import_react2.default.createElement(
      "div",
      {
        className: "notification-panel",
        "data-theme": theme,
        onClick: (e) => e.stopPropagation(),
        style: { right: `${position.right}px`, top: `${position.top}px` }
      },
      /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-panel-header" }, /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-panel-title" }, /* @__PURE__ */ import_react2.default.createElement("span", null, "\u0E01\u0E32\u0E23\u0E41\u0E08\u0E49\u0E07\u0E40\u0E15\u0E37\u0E2D\u0E19"), localNotifications.filter((n) => !n.isRead).length > 0 && /* @__PURE__ */ import_react2.default.createElement("span", { className: "notification-badge-new" }, localNotifications.filter((n) => !n.isRead).length, " \u0E43\u0E2B\u0E21\u0E48")), /* @__PURE__ */ import_react2.default.createElement("button", { className: "notification-clear-all-btn", onClick: handleClearAll }, "\u0E25\u0E49\u0E32\u0E07\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14")),
      /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-panel-content" }, newNotifications.length > 0 && /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-section" }, /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-section-header" }, /* @__PURE__ */ import_react2.default.createElement("span", null, "\u0E43\u0E2B\u0E21\u0E48")), /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-list" }, newNotifications.map((n) => renderNotifItem(n, true)))), /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-section" }, /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-section-header" }, /* @__PURE__ */ import_react2.default.createElement("span", null, "\u0E17\u0E35\u0E48\u0E1C\u0E48\u0E32\u0E19\u0E21\u0E32"), localNotifications.some((n) => !n.isRead) && /* @__PURE__ */ import_react2.default.createElement("button", { className: "notification-clear-all-btn-small", onClick: handleClearAll }, "\u0E25\u0E49\u0E32\u0E07\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14")), previousNotifications.length > 0 ? /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-list" }, previousNotifications.map((n) => renderNotifItem(n, false))) : /* @__PURE__ */ import_react2.default.createElement("p", { className: "notification-empty-inline" }, "\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E21\u0E35\u0E01\u0E32\u0E23\u0E41\u0E08\u0E49\u0E07\u0E40\u0E15\u0E37\u0E2D\u0E19\u0E17\u0E35\u0E48\u0E2D\u0E48\u0E32\u0E19\u0E41\u0E25\u0E49\u0E27")), localNotifications.length === 0 && /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-empty" }, /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-empty-icon" }, "\u{1F514}"), /* @__PURE__ */ import_react2.default.createElement("div", { className: "notification-empty-text" }, "\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E21\u0E35\u0E01\u0E32\u0E23\u0E41\u0E08\u0E49\u0E07\u0E40\u0E15\u0E37\u0E2D\u0E19")))
    ));
  }

  // src/context/LanguageContext.jsx
  var import_react3 = __toESM(require_react(), 1);
  var LanguageContext = (0, import_react3.createContext)({ lang: "th", t: (key) => key });
  function useLanguage() {
    return (0, import_react3.useContext)(LanguageContext);
  }

  // src/context/FontSizeContext.jsx
  var import_react4 = __toESM(require_react(), 1);
  var FontSizeContext = (0, import_react4.createContext)("medium");
  function useFontSize() {
    return (0, import_react4.useContext)(FontSizeContext);
  }

  // src/components/common/AppHeader.jsx
  function AppHeader({
    activeTab = "ai",
    theme: themeProp,
    user = null,
    onTabChange = () => {
    },
    onNavigateToBookings = null,
    onNavigateToAI = null,
    onNavigateToFlights = null,
    onNavigateToHotels = null,
    onNavigateToCarRentals = null,
    onNavigateToHome = null,
    onLogout = () => {
    },
    onAIClick = null,
    onNotificationClick = null,
    notificationCount = 0,
    isConnected = true,
    notifications = [],
    onSignIn = null,
    onNavigateToProfile = null,
    onNavigateToSettings = null,
    onMarkNotificationAsRead = null,
    onClearAllNotifications = null
  }) {
    const { t } = useLanguage();
    const fontSize = useFontSize();
    const themeContext = useTheme();
    const theme = themeProp ?? themeContext;
    const [isNotificationOpen, setIsNotificationOpen] = (0, import_react5.useState)(false);
    const [showUserPopup, setShowUserPopup] = (0, import_react5.useState)(false);
    const notificationButtonRef = (0, import_react5.useRef)(null);
    const userPopupRef = (0, import_react5.useRef)(null);
    const [notificationPosition, setNotificationPosition] = (0, import_react5.useState)({ right: 0, top: 0 });
    const navLinksRef = (0, import_react5.useRef)(null);
    const [sliderStyle, setSliderStyle] = (0, import_react5.useState)({ width: 0, left: 0 });
    const [isMobileMenuOpen, setIsMobileMenuOpen] = (0, import_react5.useState)(false);
    const mobileMenuRef = (0, import_react5.useRef)(null);
    (0, import_react5.useEffect)(() => {
      if (isNotificationOpen && notificationButtonRef.current) {
        const buttonRect = notificationButtonRef.current.getBoundingClientRect();
        const headerRect = notificationButtonRef.current.closest(".app-header")?.getBoundingClientRect();
        if (headerRect) {
          const right = window.innerWidth - buttonRect.right;
          const top = headerRect.bottom;
          setNotificationPosition({ right, top });
        }
      }
    }, [isNotificationOpen]);
    const updateSliderPosition = (0, import_react5.useCallback)(() => {
      if (!navLinksRef.current) return;
      const activeLink = navLinksRef.current.querySelector(`.app-nav-link.active`);
      if (activeLink) {
        const navLinksRect = navLinksRef.current.getBoundingClientRect();
        const activeLinkRect = activeLink.getBoundingClientRect();
        const left = activeLinkRect.left - navLinksRect.left;
        const width = activeLinkRect.width;
        setSliderStyle({
          width: `${width}px`,
          left: `${left}px`,
          transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
          // Smooth slide animation
        });
      }
    }, []);
    (0, import_react5.useEffect)(() => {
      const timeoutId = setTimeout(updateSliderPosition, 0);
      const handleResize = () => {
        updateSliderPosition();
      };
      window.addEventListener("resize", handleResize);
      return () => {
        clearTimeout(timeoutId);
        window.removeEventListener("resize", handleResize);
      };
    }, [activeTab, updateSliderPosition]);
    (0, import_react5.useEffect)(() => {
      const handleClickOutside = (event) => {
        if (userPopupRef.current && !userPopupRef.current.contains(event.target)) {
          setShowUserPopup(false);
        }
        if (mobileMenuRef.current && !mobileMenuRef.current.contains(event.target)) {
          setIsMobileMenuOpen(false);
        }
      };
      if (showUserPopup || isMobileMenuOpen) {
        document.addEventListener("mousedown", handleClickOutside);
      }
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }, [showUserPopup, isMobileMenuOpen]);
    const handleTabClick = (tab, e) => {
      e.preventDefault();
      setIsMobileMenuOpen(false);
      if (tab === "bookings" && onNavigateToBookings) onNavigateToBookings();
      else if (tab === "flights" && onNavigateToFlights) onNavigateToFlights();
      else if (tab === "hotels" && onNavigateToHotels) onNavigateToHotels();
      else if (tab === "ai" && onNavigateToAI) onNavigateToAI();
      else if (tab === "car-rentals" && onNavigateToCarRentals) onNavigateToCarRentals();
      onTabChange(tab);
    };
    const handleAIClick = () => {
      if (onAIClick) {
        onAIClick();
      } else {
        const chatInput = document.querySelector(".chat-input-textarea");
        if (chatInput) {
          chatInput.focus();
        }
      }
    };
    const handleNotificationClick = () => {
      setIsNotificationOpen(!isNotificationOpen);
      if (onNotificationClick) {
        onNotificationClick();
      }
    };
    return /* @__PURE__ */ import_react5.default.createElement("header", { className: "app-header", "data-theme": theme, "data-font-size": fontSize }, /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-header-content" }, /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-logo-section", onClick: onNavigateToHome, style: { cursor: "pointer" } }, /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-logo-icon" }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-plane-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" }))), /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-logo-text" }, "AI Travel Agent")), /* @__PURE__ */ import_react5.default.createElement("nav", { className: "app-nav-links app-nav-links-desktop", ref: navLinksRef }, /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-nav-slider", style: sliderStyle }), /* @__PURE__ */ import_react5.default.createElement("a", { href: "#", className: `app-nav-link ${activeTab === "flights" ? "active" : ""}`, onClick: (e) => handleTabClick("flights", e), title: "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19" }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-nav-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" })), /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-nav-text" }, t("nav.flights"))), /* @__PURE__ */ import_react5.default.createElement("a", { href: "#", className: `app-nav-link ${activeTab === "hotels" ? "active" : ""}`, onClick: (e) => handleTabClick("hotels", e), title: t("nav.hotels") }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-nav-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M7 13c1.66 0 3-1.34 3-3S8.66 7 7 7s-3 1.34-3 3 1.34 3 3 3zm12-6h-8v7H3V5H1v15h2v-3h18v3h2v-9c0-2.21-1.79-4-4-4z" })), /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-nav-text" }, t("nav.hotels"))), /* @__PURE__ */ import_react5.default.createElement("a", { href: "#", className: `app-nav-link ${activeTab === "ai" ? "active" : ""}`, onClick: (e) => handleTabClick("ai", e), title: t("nav.agent") }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-nav-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" })), /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-nav-text" }, t("nav.agent"))), /* @__PURE__ */ import_react5.default.createElement("a", { href: "#", className: `app-nav-link ${activeTab === "car-rentals" ? "active" : ""}`, onClick: (e) => handleTabClick("car-rentals", e), title: t("nav.carRentals") }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-nav-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z" })), /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-nav-text" }, t("nav.carRentals"))), /* @__PURE__ */ import_react5.default.createElement("a", { href: "#", className: `app-nav-link ${activeTab === "bookings" ? "active" : ""}`, onClick: (e) => handleTabClick("bookings", e), title: t("nav.myBookings") }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-nav-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z" })), /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-nav-text" }, t("nav.myBookings")))), /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-mobile-nav", ref: mobileMenuRef }, /* @__PURE__ */ import_react5.default.createElement(
      "button",
      {
        className: "app-mobile-menu-button",
        onClick: () => setIsMobileMenuOpen(!isMobileMenuOpen),
        "aria-label": t("nav.menu")
      },
      /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-mobile-menu-icon", fill: "currentColor", viewBox: "0 0 24 24" }, isMobileMenuOpen ? /* @__PURE__ */ import_react5.default.createElement("path", { d: "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" }) : /* @__PURE__ */ import_react5.default.createElement("path", { d: "M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z" })),
      /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-mobile-menu-text" }, activeTab === "bookings" ? t("nav.myBookings") : activeTab === "ai" ? t("nav.agent") : activeTab === "flights" ? t("nav.flights") : activeTab === "hotels" ? t("nav.hotels") : activeTab === "car-rentals" ? t("nav.carRentals") : t("nav.menu"))
    ), isMobileMenuOpen && /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-mobile-menu-dropdown" }, /* @__PURE__ */ import_react5.default.createElement("button", { className: `app-mobile-menu-item ${activeTab === "flights" ? "active" : ""}`, onClick: (e) => handleTabClick("flights", e) }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-mobile-menu-item-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" })), /* @__PURE__ */ import_react5.default.createElement("span", null, t("nav.flights")), activeTab === "flights" && /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-mobile-menu-check" }, "\u2713")), /* @__PURE__ */ import_react5.default.createElement("button", { className: `app-mobile-menu-item ${activeTab === "hotels" ? "active" : ""}`, onClick: (e) => handleTabClick("hotels", e) }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-mobile-menu-item-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M7 13c1.66 0 3-1.34 3-3S8.66 7 7 7s-3 1.34-3 3 1.34 3 3 3zm12-6h-8v7H3V5H1v15h2v-3h18v3h2v-9c0-2.21-1.79-4-4-4z" })), /* @__PURE__ */ import_react5.default.createElement("span", null, t("nav.hotels")), activeTab === "hotels" && /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-mobile-menu-check" }, "\u2713")), /* @__PURE__ */ import_react5.default.createElement("button", { className: `app-mobile-menu-item ${activeTab === "ai" ? "active" : ""}`, onClick: (e) => handleTabClick("ai", e) }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-mobile-menu-item-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" })), /* @__PURE__ */ import_react5.default.createElement("span", null, t("nav.agent")), activeTab === "ai" && /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-mobile-menu-check" }, "\u2713")), /* @__PURE__ */ import_react5.default.createElement("button", { className: `app-mobile-menu-item ${activeTab === "car-rentals" ? "active" : ""}`, onClick: (e) => handleTabClick("car-rentals", e) }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-mobile-menu-item-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z" })), /* @__PURE__ */ import_react5.default.createElement("span", null, t("nav.carRentals")), activeTab === "car-rentals" && /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-mobile-menu-check" }, "\u2713")), /* @__PURE__ */ import_react5.default.createElement("button", { className: `app-mobile-menu-item ${activeTab === "bookings" ? "active" : ""}`, onClick: (e) => handleTabClick("bookings", e) }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-mobile-menu-item-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z" })), /* @__PURE__ */ import_react5.default.createElement("span", null, t("nav.myBookings")), activeTab === "bookings" && /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-mobile-menu-check" }, "\u2713")))), /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-section" }, /* @__PURE__ */ import_react5.default.createElement(
      "button",
      {
        ref: notificationButtonRef,
        className: `app-btn-notification ${isNotificationOpen ? "active" : ""}`,
        onClick: handleNotificationClick,
        title: t("nav.notifications")
      },
      /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-notification-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { d: "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" })),
      notificationCount > 0 && /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-notification-badge" }, notificationCount)
    ), /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-menu-container", ref: userPopupRef }, user ? /* @__PURE__ */ import_react5.default.createElement(import_react5.default.Fragment, null, /* @__PURE__ */ import_react5.default.createElement(
      "div",
      {
        className: "app-user-info app-user-clickable",
        onClick: () => setShowUserPopup(!showUserPopup)
      },
      /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-avatar" }, user.profile_image || user.picture ? /* @__PURE__ */ import_react5.default.createElement(
        "img",
        {
          src: user.profile_image || user.picture,
          alt: "User",
          className: "app-user-avatar-img",
          onError: (e) => {
            e.target.style.display = "none";
            e.target.nextElementSibling.style.display = "flex";
          }
        }
      ) : null, /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-user-initial", style: { display: user.profile_image || user.picture ? "none" : "flex" } }, user.first_name && user.last_name ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}` : (user.name || "U").charAt(0).toUpperCase())),
      /* @__PURE__ */ import_react5.default.createElement("span", { className: "app-user-name" }, user.first_name || user.name || "User"),
      /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-user-dropdown-icon", fill: "none", stroke: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M19 9l-7 7-7-7" }))
    ), showUserPopup && /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup" }, /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup-header" }, /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup-avatar" }, user.profile_image || user.picture ? /* @__PURE__ */ import_react5.default.createElement(
      "img",
      {
        src: user.profile_image || user.picture,
        alt: "User",
        className: "app-user-avatar-img",
        onError: (e) => {
          e.target.style.display = "none";
          e.target.nextElementSibling.style.display = "flex";
        }
      }
    ) : null, /* @__PURE__ */ import_react5.default.createElement(
      "span",
      {
        className: "app-user-popup-initial",
        style: { display: user.profile_image || user.picture ? "none" : "flex" }
      },
      user.first_name && user.last_name ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}` : (user.name || "U").charAt(0).toUpperCase()
    )), /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup-info" }, /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup-name" }, user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : user.first_name || user.name || "User"), user.email && /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup-email" }, user.email))), /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup-divider" }), /* @__PURE__ */ import_react5.default.createElement("div", { className: "app-user-popup-actions" }, onNavigateToProfile && /* @__PURE__ */ import_react5.default.createElement(
      "button",
      {
        onClick: () => {
          setShowUserPopup(false);
          onNavigateToProfile();
        },
        className: "app-user-popup-button app-user-popup-button-profile"
      },
      /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-user-popup-icon", fill: "none", stroke: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" })),
      t("nav.editProfile")
    ), onNavigateToSettings && /* @__PURE__ */ import_react5.default.createElement(
      "button",
      {
        onClick: () => {
          setShowUserPopup(false);
          onNavigateToSettings();
        },
        className: "app-user-popup-button app-user-popup-button-settings"
      },
      /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-user-popup-icon", fill: "none", stroke: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" }), /* @__PURE__ */ import_react5.default.createElement("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M15 12a3 3 0 11-6 0 3 3 0 016 0z" })),
      t("nav.settings")
    ), onLogout && /* @__PURE__ */ import_react5.default.createElement("button", { onClick: onLogout, className: "app-user-popup-button app-user-popup-button-signout" }, /* @__PURE__ */ import_react5.default.createElement("svg", { className: "app-user-popup-icon", fill: "none", stroke: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react5.default.createElement("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" })), "Logout")))) : /* @__PURE__ */ import_react5.default.createElement(import_react5.default.Fragment, null, onSignIn ? /* @__PURE__ */ import_react5.default.createElement(
      "button",
      {
        onClick: onSignIn,
        className: "app-btn-signin"
      },
      "Sign In"
    ) : null)))), /* @__PURE__ */ import_react5.default.createElement(
      NotificationPanel,
      {
        isOpen: isNotificationOpen,
        onClose: () => setIsNotificationOpen(false),
        notificationCount,
        notifications,
        position: notificationPosition,
        onNavigateToBookings,
        onMarkAsRead: onMarkNotificationAsRead,
        onClearAll: onClearAllNotifications
      }
    ));
  }

  // src/utils/currency.js
  var RATE_TO_THB = {
    JPY: 0.25,
    USD: 35,
    EUR: 38,
    GBP: 44,
    SGD: 26,
    KRW: 0.026,
    CNY: 4.9,
    HKD: 4.5,
    THB: 1
  };
  function toThb(amount, sourceCurrency = "THB") {
    if (amount == null || Number.isNaN(Number(amount))) return null;
    const c = String(sourceCurrency || "THB").toUpperCase();
    if (c === "THB") return Math.round(Number(amount));
    const rate = RATE_TO_THB[c];
    if (rate == null) return Math.round(Number(amount));
    return Math.round(Number(amount) * rate);
  }
  function formatPriceInThb(amount, sourceCurrency = "THB") {
    const thb = toThb(amount, sourceCurrency);
    if (thb == null) return "\u2014";
    try {
      return new Intl.NumberFormat("th-TH", {
        style: "currency",
        currency: "THB",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(thb);
    } catch {
      return `\u0E3F${thb.toLocaleString("th-TH")}`;
    }
  }

  // src/components/bookings/PlanChoiceCard.jsx
  var import_react6 = __toESM(require_react(), 1);

  // src/data/airlineNames.js
  var AIRLINE_NAMES = {
    // Thailand
    TG: "Thai Airways",
    FD: "Scoot",
    XJ: "Thai AirAsia X",
    PG: "Bangkok Airways",
    VZ: "Thai Vietjet",
    WE: "Thai Smile",
    DD: "Nok Air",
    SL: "Thai Lion Air",
    OD: "Malindo Air",
    QV: "Lao Airlines",
    "8M": "Myanmar Airways International",
    FY: "Firefly",
    "2Y": "Air Andaman",
    // Singapore & Malaysia
    SQ: "Singapore Airlines",
    MI: "SilkAir",
    TR: "Scoot",
    "3K": "Jetstar Asia",
    MH: "Malaysia Airlines",
    AK: "AirAsia",
    D7: "AirAsia X",
    QD: "AirAsia",
    ZG: "AirAsia",
    I5: "AirAsia India",
    // Indonesia
    GA: "Garuda Indonesia",
    QZ: "Lion Air",
    JT: "Lion Air",
    SJ: "Sriwijaya Air",
    QG: "Citilink",
    ID: "Batik Air",
    IU: "Super Air Jet",
    // Vietnam
    VN: "Vietnam Airlines",
    VJ: "VietJet Air",
    QH: "Bamboo Airways",
    BL: "Jetstar Pacific",
    // Philippines
    PR: "Philippine Airlines",
    Z2: "Cebu Pacific",
    "5J": "Cebu Pacific",
    // Japan
    JL: "Japan Airlines",
    NH: "All Nippon Airways",
    NQ: "Air Japan",
    MM: "Peach Aviation",
    GK: "Jetstar Japan",
    JQ: "Jetstar",
    HD: "AIRDO",
    // Korea
    KE: "Korean Air",
    OZ: "Asiana Airlines",
    BX: "Air Busan",
    TW: "T'way Air",
    "7C": "Jeju Air",
    ZE: "Eastar Jet",
    // China & Hong Kong
    CA: "Air China",
    CZ: "China Southern Airlines",
    MU: "China Eastern Airlines",
    FM: "Shanghai Airlines",
    MF: "Xiamen Airlines",
    "3U": "Sichuan Airlines",
    "9C": "Spring Airlines",
    HO: "Juneyao Airlines",
    AQ: "9 Air",
    CX: "Cathay Pacific",
    KA: "Cathay Dragon",
    HX: "Hong Kong Airlines",
    UO: "Hong Kong Express",
    NX: "Air Macau",
    CI: "China Airlines",
    // Taiwan
    BR: "EVA Air",
    // India
    UK: "Vistara",
    "6E": "IndiGo",
    SG: "SpiceJet",
    AI: "Air India",
    IX: "Air India Express",
    I9: "Air India Regional",
    G8: "Go First",
    W2: "Flexflight",
    LB: "Air Costa",
    // Middle East
    EK: "Emirates",
    QR: "Qatar Airways",
    EY: "Etihad",
    FZ: "flydubai",
    GF: "Gulf Air",
    WY: "Oman Air",
    KU: "Kuwait Airways",
    RJ: "Royal Jordanian",
    SV: "Saudia",
    XY: "Flynas",
    PC: "Pegasus Airlines",
    TK: "Turkish Airlines",
    VF: "AJet",
    "3O": "Air Arabia Maroc",
    G9: "Air Arabia",
    "5W": "Wizz Air Abu Dhabi",
    // Central Asia
    KC: "Air Astana",
    HY: "Uzbekistan Airways",
    // Russia & CIS
    SU: "Aeroflot",
    S7: "S7 Airlines",
    U6: "Ural Airlines",
    // Europe
    BA: "British Airways",
    AF: "Air France",
    LH: "Lufthansa",
    KL: "KLM",
    AY: "Finnair",
    IB: "Iberia",
    LX: "Swiss International",
    OS: "Austrian Airlines",
    SK: "Scandinavian Airlines",
    TP: "TAP Portugal",
    UX: "Air Europa",
    SN: "Brussels Airlines",
    EI: "Aer Lingus",
    JU: "Air Serbia",
    A3: "Aegean Airlines",
    W6: "Wizz Air",
    U2: "easyJet",
    FR: "Ryanair",
    // North America
    UA: "United Airlines",
    AA: "American Airlines",
    DL: "Delta Air Lines",
    WN: "Southwest Airlines",
    B6: "JetBlue",
    AS: "Alaska Airlines",
    NK: "Spirit Airlines",
    F9: "Frontier Airlines",
    AC: "Air Canada",
    RV: "Air Canada Rouge",
    // Oceania
    QF: "Qantas",
    NZ: "Air New Zealand",
    // Brunei & Others
    BI: "Royal Brunei Airlines",
    UL: "SriLankan Airlines",
    H1: "Hahn Air"
  };
  var AIRLINE_DOMAINS = {
    TG: "thaiairways.com",
    FD: "flyscoot.com",
    XJ: "thaiairasia.com",
    PG: "bangkokair.com",
    VZ: "thaivietjet.com",
    WE: "thaismileair.com",
    DD: "nokair.com",
    SL: "thailionair.com",
    OD: "malindoair.com",
    QV: "laoairlines.com",
    "8M": "maiair.com",
    FY: "fireflyz.com.my",
    SQ: "singaporeair.com",
    TR: "scoot.com",
    "3K": "jetstar.com",
    MH: "malaysiaairlines.com",
    AK: "airasia.com",
    D7: "airasia.com",
    GA: "garuda-indonesia.com",
    QZ: "lionair.co.id",
    JT: "lionair.co.id",
    VN: "vietnamairlines.com",
    VJ: "vietjetair.com",
    QH: "bambooairways.com",
    PR: "philippineairlines.com",
    Z2: "cebupacificair.com",
    "5J": "cebupacificair.com",
    JL: "jal.co.jp",
    NH: "ana.co.jp",
    KE: "koreanair.com",
    OZ: "flyasiana.com",
    CA: "airchina.com.cn",
    CZ: "csair.com",
    MU: "ceair.com",
    FM: "shanghai-air.com",
    MF: "xiamenair.com",
    CX: "cathaypacific.com",
    KA: "cathaydragon.com",
    BR: "evaair.com",
    CI: "china-airlines.com",
    EK: "emirates.com",
    QR: "qatarairways.com",
    EY: "etihad.com",
    FZ: "flydubai.com",
    GF: "gulfair.com",
    TK: "turkishairlines.com",
    BA: "britishairways.com",
    AF: "airfrance.com",
    LH: "lufthansa.com",
    KL: "klm.com",
    UA: "united.com",
    AA: "aa.com",
    DL: "delta.com",
    QF: "qantas.com",
    NZ: "airnewzealand.com",
    H1: "hahnair.com",
    UK: "airvistara.com",
    "6E": "goindigo.in",
    SG: "spicejet.com",
    W2: "flexflight.com"
  };

  // src/data/airportNames.js
  var AIRPORT_NAMES = {
    // Thailand
    BKK: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2A\u0E38\u0E27\u0E23\u0E23\u0E13\u0E20\u0E39\u0E21\u0E34",
    DMK: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E14\u0E2D\u0E19\u0E40\u0E21\u0E37\u0E2D\u0E07",
    CNX: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E0A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48",
    HKT: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E20\u0E39\u0E40\u0E01\u0E47\u0E15",
    USM: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2A\u0E21\u0E38\u0E22",
    KBV: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E01\u0E23\u0E30\u0E1A\u0E35\u0E48",
    UTH: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2D\u0E38\u0E14\u0E23\u0E18\u0E32\u0E19\u0E35",
    HDY: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2B\u0E32\u0E14\u0E43\u0E2B\u0E0D\u0E48",
    // Myanmar
    RGN: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E22\u0E48\u0E32\u0E07\u0E01\u0E38\u0E49\u0E07",
    MDL: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E21\u0E31\u0E13\u0E11\u0E30\u0E40\u0E25\u0E22\u0E4C",
    // Japan
    NRT: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E19\u0E32\u0E23\u0E34\u0E15\u0E30",
    HND: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2E\u0E32\u0E40\u0E19\u0E14\u0E30",
    KIX: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E04\u0E31\u0E19\u0E44\u0E0B",
    NGO: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E0B\u0E47\u0E19\u0E41\u0E17\u0E23\u0E23\u0E4C",
    FUK: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E1F\u0E38\u0E01\u0E38\u0E42\u0E2D\u0E01\u0E30",
    // Korea
    ICN: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2D\u0E34\u0E19\u0E0A\u0E2D\u0E19",
    GMP: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E01\u0E34\u0E21\u0E42\u0E1B",
    // China
    PEK: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E1B\u0E31\u0E01\u0E01\u0E34\u0E48\u0E07",
    PVG: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E0B\u0E35\u0E48\u0E22\u0E07\u0E44\u0E2E\u0E49\u0E1C\u0E39\u0E48\u0E15\u0E07",
    CAN: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E01\u0E27\u0E32\u0E07\u0E42\u0E08\u0E27",
    TPE: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E44\u0E15\u0E49\u0E2B\u0E27\u0E31\u0E19\u0E40\u0E15\u0E32\u0E1B\u0E35",
    HKG: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2E\u0E48\u0E2D\u0E07\u0E01\u0E07",
    MFM: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E21\u0E32\u0E40\u0E01\u0E4A\u0E32",
    // Singapore & Malaysia
    SIN: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E0A\u0E32\u0E07\u0E07\u0E35",
    KUL: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E01\u0E31\u0E27\u0E25\u0E32\u0E25\u0E31\u0E21\u0E40\u0E1B\u0E2D\u0E23\u0E4C",
    PEN: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E1B\u0E35\u0E19\u0E31\u0E07",
    // Vietnam
    SGN: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E42\u0E2E\u0E08\u0E34\u0E21\u0E34\u0E19\u0E2B\u0E4C",
    HAN: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2E\u0E32\u0E19\u0E2D\u0E22",
    DAD: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E14\u0E32\u0E19\u0E31\u0E07",
    // Indonesia
    CGK: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E08\u0E32\u0E01\u0E32\u0E23\u0E4C\u0E15\u0E32",
    DPS: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E1A\u0E32\u0E2B\u0E25\u0E35",
    // Philippines
    MNL: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E21\u0E30\u0E19\u0E34\u0E25\u0E32",
    CEB: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E0B\u0E1A\u0E39",
    // Cambodia & Laos
    REP: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E2A\u0E35\u0E22\u0E21\u0E40\u0E23\u0E35\u0E22\u0E1A",
    PNH: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E1E\u0E19\u0E21\u0E40\u0E1B\u0E0D",
    VTE: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E27\u0E35\u0E22\u0E07\u0E08\u0E31\u0E19\u0E17\u0E19\u0E4C",
    LPQ: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2B\u0E25\u0E27\u0E07\u0E1E\u0E23\u0E30\u0E1A\u0E32\u0E07",
    // India
    DEL: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E19\u0E34\u0E27\u0E40\u0E14\u0E25\u0E35",
    BOM: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E21\u0E38\u0E21\u0E44\u0E1A",
    MAA: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E08\u0E19\u0E44\u0E19",
    // Middle East
    DXB: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E14\u0E39\u0E44\u0E1A",
    DOH: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E42\u0E14\u0E2E\u0E32",
    BAH: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E1A\u0E32\u0E2B\u0E4C\u0E40\u0E23\u0E19",
    KWI: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E04\u0E39\u0E40\u0E27\u0E15",
    AUH: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2D\u0E32\u0E1A\u0E39\u0E14\u0E32\u0E1A\u0E35",
    // Europe
    LHR: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E25\u0E2D\u0E19\u0E14\u0E2D\u0E19\u0E2E\u0E35\u0E17\u0E42\u0E18\u0E23\u0E27\u0E4C",
    CDG: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E1B\u0E32\u0E23\u0E35\u0E2A\u0E0A\u0E32\u0E23\u0E4C\u0E25\u0E2A\u0E4C de \u0E01\u0E2D\u0E25",
    FRA: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E41\u0E1F\u0E23\u0E07\u0E01\u0E4C\u0E40\u0E1F\u0E34\u0E23\u0E4C\u0E15",
    AMS: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E2D\u0E31\u0E21\u0E2A\u0E40\u0E15\u0E2D\u0E23\u0E4C\u0E14\u0E31\u0E21",
    // Australia
    SYD: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E0B\u0E34\u0E14\u0E19\u0E35\u0E22\u0E4C",
    MEL: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E40\u0E21\u0E25\u0E40\u0E1A\u0E34\u0E23\u0E4C\u0E19",
    // US
    LAX: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E25\u0E2D\u0E2A\u0E41\u0E2D\u0E19\u0E40\u0E08\u0E25\u0E34\u0E2A",
    SFO: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E0B\u0E32\u0E19\u0E1F\u0E23\u0E32\u0E19\u0E0B\u0E34\u0E2A\u0E42\u0E01",
    JFK: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E19\u0E34\u0E27\u0E22\u0E2D\u0E23\u0E4C\u0E01\u0E40\u0E08\u0E40\u0E2D\u0E1F\u0E40\u0E04",
    ORD: "\u0E17\u0E48\u0E32\u0E2D\u0E32\u0E01\u0E32\u0E28\u0E22\u0E32\u0E19\u0E0A\u0E34\u0E04\u0E32\u0E42\u0E01"
  };
  function getAirportDisplay(code) {
    if (!code) return "";
    const c = String(code).toUpperCase();
    const name = AIRPORT_NAMES[c];
    return name ? `${c} (${name})` : c;
  }

  // src/components/bookings/PlanChoiceCard.jsx
  function calculateLayoverTime(prevSegment, nextSegment) {
    if (!prevSegment || !nextSegment) return null;
    const prevArrival = prevSegment.arrive_at || prevSegment.depart_at;
    const nextDeparture = nextSegment.depart_at || nextSegment.depart_at;
    if (!prevArrival || !nextDeparture) return null;
    try {
      const prevTime = new Date(prevArrival);
      const nextTime = new Date(nextDeparture);
      const diffMs = nextTime.getTime() - prevTime.getTime();
      const diffHours = Math.floor(diffMs / (1e3 * 60 * 60));
      const diffMinutes = Math.floor(diffMs % (1e3 * 60 * 60) / (1e3 * 60));
      if (diffHours < 0 || diffMinutes < 0) return null;
      if (diffHours > 0) {
        return `${diffHours}\u0E0A\u0E21 ${diffMinutes}\u0E19\u0E32\u0E17\u0E35`;
      } else {
        return `${diffMinutes}\u0E19\u0E32\u0E17\u0E35`;
      }
    } catch (e) {
    }
  }
  var getDuffelLogoUrl = (code) => {
    const c = String(code || "").toUpperCase();
    if (!c || c.length !== 2) return null;
    return `https://assets.duffel.com/img/airlines/for-light-background/full-color-logo/${c}.svg`;
  };
  var getKiwiLogoUrl = (code) => `https://images.kiwi.com/airlines/64/${String(code).toUpperCase()}.png`;
  var getClearbitLogoUrl = (code) => {
    const domain = AIRLINE_DOMAINS[String(code).toUpperCase()];
    return domain ? `https://logo.clearbit.com/${domain}` : null;
  };
  var getGoogleFaviconUrl = (code) => {
    const domain = AIRLINE_DOMAINS[String(code).toUpperCase()];
    return domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=64` : null;
  };
  function AirlineLogo({ carrierCode, size = 40, style = {} }) {
    const [showFallback, setShowFallback] = import_react6.default.useState(false);
    const kiwiUrl = carrierCode ? getKiwiLogoUrl(carrierCode) : null;
    const duffelUrl = carrierCode ? getDuffelLogoUrl(carrierCode) : null;
    const clearbitUrl = carrierCode ? getClearbitLogoUrl(carrierCode) : null;
    const googleFaviconUrl = carrierCode ? getGoogleFaviconUrl(carrierCode) : null;
    const initialSrc = duffelUrl || kiwiUrl;
    const handleError = (e) => {
      const img = e.target;
      const src = (img.src || "").toLowerCase();
      const isDuffel = src.includes("assets.duffel.com");
      const isKiwi = src.includes("images.kiwi.com");
      const isClearbit = src.includes("logo.clearbit.com");
      if (isDuffel && kiwiUrl) {
        img.src = kiwiUrl;
        return;
      }
      if (isKiwi && clearbitUrl) {
        img.src = clearbitUrl;
        return;
      }
      if (isClearbit && googleFaviconUrl) {
        img.src = googleFaviconUrl;
        return;
      }
      setShowFallback(true);
      img.style.display = "none";
    };
    if (!carrierCode || showFallback || !initialSrc) {
      return /* @__PURE__ */ import_react6.default.createElement("div", { style: {
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: "6px",
        background: "rgba(255, 255, 255, 0.1)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: `${Math.max(10, size * 0.35)}px`,
        fontWeight: "600",
        color: "#fff",
        ...style
      } }, "\u2708\uFE0F ", carrierCode || "N/A");
    }
    return /* @__PURE__ */ import_react6.default.createElement(
      "img",
      {
        src: initialSrc,
        alt: `${carrierCode} logo`,
        style: {
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: "6px",
          objectFit: "contain",
          background: "rgba(255, 255, 255, 0.05)",
          padding: "4px",
          display: showFallback ? "none" : "block",
          ...style
        },
        onError: handleError
      }
    );
  }
  function getAirlineName(code) {
    if (!code) return "Unknown";
    return AIRLINE_NAMES[code.toUpperCase()] || code;
  }
  function getAircraftName(code) {
    if (!code) return "Unknown";
    const aircraftNames = {
      "737": "Boeing 737",
      "738": "Boeing 737-800",
      "739": "Boeing 737-900",
      "73H": "Boeing 737-800",
      "73M": "Boeing 737 MAX",
      "320": "Airbus A320",
      "321": "Airbus A321",
      "32A": "Airbus A320",
      "32B": "Airbus A321",
      "32N": "Airbus A320neo",
      "32Q": "Airbus A321neo",
      "330": "Airbus A330",
      "332": "Airbus A330-200",
      "333": "Airbus A330-300",
      "350": "Airbus A350",
      "351": "Airbus A350-1000",
      "359": "Airbus A350-900",
      "380": "Airbus A380",
      "777": "Boeing 777",
      "77W": "Boeing 777-300ER",
      "787": "Boeing 787",
      "788": "Boeing 787-8",
      "789": "Boeing 787-9",
      "78X": "Boeing 787-10",
      "AT7": "ATR 72",
      "ATR": "ATR 72",
      "CRJ": "Bombardier CRJ",
      "E90": "Embraer E190",
      "E95": "Embraer E195"
    };
    return aircraftNames[code.toUpperCase()] || `\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07\u0E1A\u0E34\u0E19 ${code}`;
  }
  function formatDuration(durationStr) {
    if (!durationStr || typeof durationStr !== "string") return "";
    if (durationStr.startsWith("PT")) {
      let hours = 0;
      let minutes = 0;
      try {
        if (durationStr.includes("H")) {
          const hoursPart = durationStr.split("H")[0].replace("PT", "");
          hours = parseInt(hoursPart) || 0;
          const remaining = durationStr.split("H")[1] || "";
          if (remaining.includes("M")) {
            const minutesPart = remaining.split("M")[0];
            minutes = parseInt(minutesPart) || 0;
          }
        } else {
          const remaining = durationStr.replace("PT", "");
          if (remaining.includes("M")) {
            const minutesPart = remaining.split("M")[0];
            minutes = parseInt(minutesPart) || 0;
          }
        }
        const parts = [];
        if (hours > 0) {
          parts.push(`${hours}\u0E0A\u0E21`);
        }
        if (minutes > 0) {
          parts.push(`${minutes}\u0E19\u0E32\u0E17\u0E35`);
        }
        return parts.length > 0 ? parts.join(" ") : "\u0E44\u0E21\u0E48\u0E23\u0E30\u0E1A\u0E38";
      } catch (e) {
        return durationStr;
      }
    }
    return durationStr;
  }
  function calculateCO2e(distanceKm) {
    if (!distanceKm || distanceKm <= 0) return 0;
    const estimatedCO2 = Math.round(distanceKm * 0.22);
    return estimatedCO2;
  }
  function getFlightType(segments) {
    if (!segments || segments.length === 0) return "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07";
    return segments.length > 1 ? "\u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07" : "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07";
  }
  function getArrivalTimeDisplay(arriveAt, arrivePlus) {
    if (!arriveAt) return "";
    let timeStr = "";
    if (typeof arriveAt === "string" && arriveAt.includes("T")) {
      const timePart = arriveAt.split("T")[1]?.split(":").slice(0, 2).join(":") || "";
      timeStr = timePart;
    } else if (typeof arriveAt === "string") {
      timeStr = arriveAt;
    }
    if (arrivePlus) {
      return `${timeStr} ${arrivePlus}`;
    }
    return timeStr;
  }
  function getFirstSegment(flight) {
    return flight?.segments?.length ? flight.segments[0] : null;
  }
  function getLastSegment(flight) {
    return flight?.segments?.length ? flight.segments[flight.segments.length - 1] : null;
  }
  function stopsLabel(flight) {
    const n = flight?.segments?.length || 0;
    if (!n) return null;
    const stops = Math.max(0, n - 1);
    return stops === 0 ? "Non-stop" : `${stops} stop`;
  }
  function carriersLabel(flight) {
    const segs = flight?.segments || [];
    if (!segs.length) return null;
    const carriers = [];
    for (const s of segs) {
      const c = s?.carrier;
      if (c && !carriers.includes(c)) carriers.push(c);
    }
    return carriers.length ? carriers.join(", ") : null;
  }
  function PlanChoiceCard({ choice, onSelect, cardStyle }) {
    const [showItinerary, setShowItinerary] = (0, import_react6.useState)(false);
    const [showFlightDetails, setShowFlightDetails] = (0, import_react6.useState)(false);
    const {
      id,
      label,
      description,
      tags,
      recommended,
      flight,
      flight_details,
      // ✅ ข้อมูลรายละเอียดไฟท์บิน
      hotel,
      car,
      // ✅ รถเช่า
      transport,
      currency,
      total_price,
      total_price_text,
      price_breakdown,
      title,
      // เผื่อ backend ส่ง title มา (เช่น "🟢 ช้อยส์ 1 (แนะนำ) ...")
      ground_transport,
      // ✅ ข้อมูลการเดินทาง/ขนส่ง
      itinerary,
      // ✅ ข้อมูล itinerary
      is_fastest,
      // ✅ เร็วสุดสะดวกสุด
      is_day_trip,
      // ✅ 1 วันไปกลับ
      display_text,
      // ✅ ข้อความที่ backend สร้างไว้แล้ว (สำหรับ slot-based workflow)
      slot
      // ✅ slot type (flight, hotel, etc.)
    } = choice || {};
    const displayCurrency = price_breakdown && price_breakdown.currency || currency || flight?.currency || hotel?.currency || "THB";
    const displayTotalPrice = typeof total_price === "number" ? formatPriceInThb(total_price, displayCurrency) : total_price_text || null;
    const flightDirection = choice?.flight_direction ?? (flight?.segments?.[0]?.direction && String(flight.segments[0].direction).includes("\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A") ? "inbound" : flight?.segments?.[0]?.direction && String(flight.segments[0].direction).includes("\u0E02\u0E32\u0E44\u0E1B") ? "outbound" : null);
    const segmentsForDisplay = (() => {
      const segs = flight?.segments || [];
      if (!segs.length) return segs;
      if (flightDirection === "outbound") return segs.filter((s) => s?.direction && String(s.direction).includes("\u0E02\u0E32\u0E44\u0E1B"));
      if (flightDirection === "inbound") return segs.filter((s) => s?.direction && String(s.direction).includes("\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A"));
      return segs;
    })();
    const displayFlight = segmentsForDisplay.length ? { ...flight, segments: segmentsForDisplay } : flight;
    const firstSeg = getFirstSegment(displayFlight);
    const lastSeg = getLastSegment(displayFlight);
    const flightRoute = firstSeg && lastSeg ? `${firstSeg.from} \u2192 ${lastSeg.to}` : null;
    const flightTime = firstSeg && lastSeg ? `${firstSeg.depart_time || ""} \u2192 ${lastSeg.arrive_time || ""}${lastSeg.arrive_plus ? ` ${lastSeg.arrive_plus}` : ""}`.trim() : null;
    const flightStops = stopsLabel(displayFlight);
    const flightCarriers = carriersLabel(flight);
    const flightPrice = formatPriceInThb(
      typeof flight?.price_total === "number" ? flight.price_total : null,
      flight?.currency || displayCurrency
    );
    let totalJourneyTime = null;
    if (firstSeg && lastSeg && displayFlight?.segments && displayFlight.segments.length > 0) {
      try {
        const firstDepart = firstSeg.depart_at || firstSeg.depart_time;
        let lastArrive = lastSeg.arrive_at || lastSeg.arrive_time;
        if (lastArrive && lastSeg.arrive_plus) {
          try {
            const arriveDate = new Date(lastArrive);
            const plusMatch = String(lastSeg.arrive_plus).match(/\+(\d+)/);
            if (plusMatch) {
              const plusDays = parseInt(plusMatch[1]) || 0;
              arriveDate.setDate(arriveDate.getDate() + plusDays);
              lastArrive = arriveDate.toISOString();
            }
          } catch (e) {
          }
        }
        if (!firstDepart || !lastArrive) {
          let totalSeconds = 0;
          const parseDuration = (durationStr) => {
            if (!durationStr || typeof durationStr !== "string" || !durationStr.startsWith("PT")) return 0;
            let hours = 0, minutes = 0;
            const hourMatch = durationStr.match(/(\d+)H/);
            const minuteMatch = durationStr.match(/(\d+)M/);
            if (hourMatch) hours = parseInt(hourMatch[1]);
            if (minuteMatch) minutes = parseInt(minuteMatch[1]);
            return hours * 3600 + minutes * 60;
          };
          for (const seg of displayFlight.segments) {
            if (seg.duration) {
              totalSeconds += parseDuration(seg.duration);
            }
          }
          for (let i = 0; i < displayFlight.segments.length - 1; i++) {
            const prevSeg = displayFlight.segments[i];
            const nextSeg = displayFlight.segments[i + 1];
            const layover = calculateLayoverTime(prevSeg, nextSeg);
            if (layover) {
              const hourMatch = layover.match(/(\d+)ชม/);
              const minuteMatch = layover.match(/(\d+)นาที/);
              if (hourMatch) totalSeconds += parseInt(hourMatch[1]) * 3600;
              if (minuteMatch) totalSeconds += parseInt(minuteMatch[1]) * 60;
            }
          }
          if (totalSeconds > 0) {
            const totalHours = Math.floor(totalSeconds / 3600);
            const totalMinutes = Math.floor(totalSeconds % 3600 / 60);
            if (totalHours > 0) {
              totalJourneyTime = `${totalHours}\u0E0A\u0E21 ${totalMinutes}\u0E19\u0E32\u0E17\u0E35`;
            } else {
              totalJourneyTime = `${totalMinutes}\u0E19\u0E32\u0E17\u0E35`;
            }
          }
        } else {
          const firstTime = new Date(firstDepart);
          const lastTime = new Date(lastArrive);
          if (!isNaN(firstTime.getTime()) && !isNaN(lastTime.getTime())) {
            const diffMs = lastTime.getTime() - firstTime.getTime();
            if (diffMs > 0) {
              const totalHours = Math.floor(diffMs / (1e3 * 60 * 60));
              const totalMinutes = Math.floor(diffMs % (1e3 * 60 * 60) / (1e3 * 60));
              if (totalHours > 0) {
                totalJourneyTime = `${totalHours}\u0E0A\u0E21 ${totalMinutes}\u0E19\u0E32\u0E17\u0E35`;
              } else {
                totalJourneyTime = `${totalMinutes}\u0E19\u0E32\u0E17\u0E35`;
              }
            }
          }
        }
        if (totalJourneyTime) {
        }
      } catch (e) {
      }
    }
    const hotelName = hotel?.hotelName || null;
    const hotelNights = hotel?.nights != null ? hotel.nights : null;
    const hotelBoard = hotel?.boardType || null;
    const toFinite = (v) => typeof v === "number" ? v : typeof v === "string" && v.trim() ? Number(v) : NaN;
    const pickFirstNonNull = (...vals) => {
      for (const v of vals) {
        const n = toFinite(v);
        if (Number.isFinite(n)) return n;
      }
      return null;
    };
    const hotelPricingCurrency = hotel?.booking?.pricing?.currency || hotel?.currency || displayCurrency;
    const hotelTotalAmount = pickFirstNonNull(
      hotel?.booking?.pricing?.total_amount,
      hotel?.price_total,
      choice?.price_amount,
      choice?.total_price,
      choice?.price
    );
    const hotelPricePerNight = pickFirstNonNull(
      hotel?.booking?.pricing?.price_per_night,
      hotelTotalAmount != null && hotelNights != null && hotelNights > 0 ? hotelTotalAmount / hotelNights : null
    );
    const hotelTaxesRaw = toFinite(hotel?.booking?.pricing?.taxes_and_fees);
    const hotelTaxesAndFees = Number.isFinite(hotelTaxesRaw) && hotelTaxesRaw > 0 ? hotelTaxesRaw : null;
    const hotelPrice = formatPriceInThb(
      hotelTotalAmount,
      hotelPricingCurrency
    );
    const transportMode = transport?.mode || null;
    const transportNote = transport?.note || null;
    const breakdownFlight = typeof price_breakdown?.flight_total === "number" ? formatPriceInThb(price_breakdown.flight_total, displayCurrency) : null;
    const breakdownHotel = typeof price_breakdown?.hotel_total === "number" ? formatPriceInThb(price_breakdown.hotel_total, displayCurrency) : null;
    const transportType = transport?.type || null;
    const transportData = transport?.data || null;
    const breakdownTransport = typeof price_breakdown?.transport_total === "number" ? formatPriceInThb(price_breakdown.transport_total, displayCurrency) : null;
    return /* @__PURE__ */ import_react6.default.createElement("div", { className: `plan-card ${recommended ? "plan-card-recommended" : ""}`, style: cardStyle }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-title" }, /* @__PURE__ */ import_react6.default.createElement("span", { className: "plan-card-label" }, title ? title : `\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${id}${label ? ` \u2014 ${label}` : ""}`), recommended && (!tags || !tags.includes("\u0E41\u0E19\u0E30\u0E19\u0E33")) && /* @__PURE__ */ import_react6.default.createElement("span", { className: "plan-card-tag" }, "\u0E41\u0E19\u0E30\u0E19\u0E33"), (choice?.flight_direction === "outbound" || firstSeg?.direction && String(firstSeg.direction).includes("\u0E02\u0E32\u0E44\u0E1B")) && /* @__PURE__ */ import_react6.default.createElement("span", { className: "plan-card-tag", style: { background: "rgba(33, 150, 243, 0.25)", color: "#1976d2", marginLeft: "6px", fontSize: "13px", padding: "3px 10px" } }, "\u{1F6EB} \u0E02\u0E32\u0E44\u0E1B"), (choice?.flight_direction === "inbound" || firstSeg?.direction && String(firstSeg.direction).includes("\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A")) && /* @__PURE__ */ import_react6.default.createElement("span", { className: "plan-card-tag", style: { background: "rgba(156, 39, 176, 0.25)", color: "#7b1fa2", marginLeft: "6px", fontSize: "13px", padding: "3px 10px" } }, "\u{1F6EC} \u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A"), (choice?.is_non_stop || flight && flightStops === "Non-stop") && flight && (!tags || !tags.includes("\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07")) && /* @__PURE__ */ import_react6.default.createElement("span", { className: "plan-card-tag", style: {
      background: "rgba(227, 242, 253, 0.3)",
      color: "#1976d2",
      marginLeft: "6px",
      fontSize: "13px",
      padding: "3px 10px",
      backdropFilter: "blur(4px)"
    } }, "\u2708\uFE0F \u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07")), tags && Array.isArray(tags) && tags.length > 0 && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-tags" }, [...new Set(tags)].filter((tag) => !["Amadeus", "\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07", "\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E17\u0E31\u0E19\u0E17\u0E35", "Google", "\u0E44\u0E21\u0E48\u0E43\u0E0A\u0E48\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07"].includes(tag)).filter((tag) => {
      if (tag === "\u0E41\u0E19\u0E30\u0E19\u0E33" && recommended) return false;
      if (tag === "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07" && (choice?.is_non_stop || flight && flightStops === "Non-stop")) return false;
      return true;
    }).map((tag, idx) => /* @__PURE__ */ import_react6.default.createElement("span", { key: idx, className: "plan-tag-pill" }, tag)))), description && /* @__PURE__ */ import_react6.default.createElement("p", { className: "plan-card-desc" }, description), flight && displayFlight?.segments && displayFlight.segments.length > 0 && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-title" }, "\u2708\uFE0F \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-body" }, firstSeg && lastSeg && /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      marginBottom: "16px",
      padding: "12px",
      background: "rgba(255, 255, 255, 0.08)",
      borderRadius: "8px",
      border: "1px solid rgba(255, 255, 255, 0.15)"
    } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", flexWrap: "wrap" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "12px", minWidth: "120px" } }, /* @__PURE__ */ import_react6.default.createElement(
      AirlineLogo,
      {
        carrierCode: firstSeg.carrier,
        size: 40
      }
    ), /* @__PURE__ */ import_react6.default.createElement("div", null, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontSize: "14px", fontWeight: "600" } }, getAirlineName(firstSeg.carrier)), /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontSize: "12px", opacity: 0.7 } }, firstSeg.carrier, firstSeg.flight_number || ""))), /* @__PURE__ */ import_react6.default.createElement("div", { style: { flex: 1, minWidth: "200px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "16px", fontWeight: "600" } }, firstSeg.depart_time || "N/A"), /* @__PURE__ */ import_react6.default.createElement("span", { style: { opacity: 0.6 } }, "\u2013"), /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "16px", fontWeight: "600" } }, getArrivalTimeDisplay(lastSeg.arrive_at, lastSeg.arrive_plus) || lastSeg.arrive_time || "N/A")), /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", fontSize: "13px", opacity: 0.8 } }, totalJourneyTime && /* @__PURE__ */ import_react6.default.createElement("span", null, "\u23F1\uFE0F ", totalJourneyTime), flightRoute && /* @__PURE__ */ import_react6.default.createElement("span", null, "\u2022"), flightRoute && /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F4CD} ", flightRoute), flightStops && /* @__PURE__ */ import_react6.default.createElement("span", null, "\u2022"), /* @__PURE__ */ import_react6.default.createElement("span", { style: {
      padding: "2px 6px",
      borderRadius: "4px",
      fontSize: "12px",
      fontWeight: "500",
      background: flightStops === "Non-stop" ? "rgba(74, 222, 128, 0.2)" : "rgba(255, 193, 7, 0.2)",
      color: flightStops === "Non-stop" ? "#4ade80" : "#ffc107"
    } }, getFlightType(displayFlight.segments) === "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07" ? "\u2708\uFE0F \u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07" : "\u{1F500} \u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07")), displayFlight.segments.length > 1 && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "6px", fontSize: "12px", opacity: 0.7 } }, displayFlight.segments.slice(0, -1).map((seg, idx) => {
      const nextSeg = displayFlight.segments[idx + 1];
      const layover = calculateLayoverTime(seg, nextSeg);
      return layover ? /* @__PURE__ */ import_react6.default.createElement("span", { key: idx, style: { marginRight: "8px" } }, seg.to ? `\u0E23\u0E2D\u0E17\u0E35\u0E48 ${getAirportDisplay(seg.to)}` : "\u0E23\u0E2D\u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07", " (", layover, ")") : null;
    })), firstSeg.from && lastSeg.to && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "6px", fontSize: "12px", opacity: 0.7 } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F331} CO2e: ~", calculateCO2e(flightRoute ? 1500 : 0), " \u0E01\u0E01. (\u0E1B\u0E23\u0E30\u0E21\u0E32\u0E13\u0E01\u0E32\u0E23)"))), /* @__PURE__ */ import_react6.default.createElement("div", { style: { textAlign: "right", minWidth: "100px" } }, flightPrice && /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontSize: "18px", fontWeight: "700", marginBottom: "4px" } }, flightPrice)))), displayFlight.segments && displayFlight.segments.length > 0 ? /* @__PURE__ */ import_react6.default.createElement(import_react6.default.Fragment, null, displayFlight.segments.map((seg, idx) => {
      const totalFlightPrice = typeof flight?.price_total === "number" ? flight.price_total : null;
      let segmentPrice = null;
      if (totalFlightPrice && seg.duration) {
        const parseDuration = (durationStr) => {
          if (!durationStr || typeof durationStr !== "string" || !durationStr.startsWith("PT")) return 0;
          let hours = 0, minutes = 0;
          const hourMatch = durationStr.match(/(\d+)H/);
          const minuteMatch = durationStr.match(/(\d+)M/);
          if (hourMatch) hours = parseInt(hourMatch[1]);
          if (minuteMatch) minutes = parseInt(minuteMatch[1]);
          return hours * 3600 + minutes * 60;
        };
        const totalDuration = displayFlight.segments?.reduce((sum, s) => {
          return sum + parseDuration(s.duration || "");
        }, 0) || 0;
        const segDurationStr = seg.duration;
        const segSeconds = parseDuration(segDurationStr);
        if (totalDuration > 0) {
          segmentPrice = Math.round(totalFlightPrice * segSeconds / totalDuration);
        }
      }
      const nextSegment = idx < displayFlight.segments.length - 1 ? displayFlight.segments[idx + 1] : null;
      const layoverTime = calculateLayoverTime(seg, nextSegment);
      return /* @__PURE__ */ import_react6.default.createElement("div", { key: idx, style: { marginBottom: idx < displayFlight.segments.length - 1 ? "12px" : "0" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "6px", fontSize: "16px", lineHeight: "1.4", display: "flex", alignItems: "center", gap: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, seg.direction === "\u0E02\u0E32\u0E44\u0E1B" ? "\u{1F6EB}" : seg.direction === "\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A" ? "\u{1F6EC}" : "\u2708\uFE0F"), /* @__PURE__ */ import_react6.default.createElement("span", null, seg.direction ? seg.direction : idx === 0 ? "\u0E02\u0E32\u0E44\u0E1B" : idx === 1 && displayFlight.segments.length === 2 ? "\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A" : `\u0E44\u0E1F\u0E25\u0E17\u0E4C ${idx + 1}`)), /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontSize: "16px", marginBottom: "4px", lineHeight: "1.5" } }, "\u0E2A\u0E32\u0E22\u0E01\u0E32\u0E23\u0E1A\u0E34\u0E19: ", getAirlineName(seg.carrier), seg.carrier && seg.flight_number ? ` \u2022 ${seg.carrier}${seg.flight_number}` : seg.flight_number ? ` \u2022 ${seg.flight_number}` : "", seg.operating && seg.operating !== seg.carrier && /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "14px", fontStyle: "italic", marginLeft: "6px", opacity: 0.8 } }, "(Operated by ", getAirlineName(seg.operating), ")")), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07: ", seg.from || "-", " \u2192 ", seg.to || "-", seg.departure_terminal && /* @__PURE__ */ import_react6.default.createElement("span", { style: { marginLeft: "4px" } }, "(Term ", seg.departure_terminal, ")"), seg.arrival_terminal && /* @__PURE__ */ import_react6.default.createElement("span", { style: { marginLeft: "4px" } }, "\u2192 (Term ", seg.arrival_terminal, ")")), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E2D\u0E2D\u0E01: ", seg.depart_time || "-", " \u2192 \u0E16\u0E36\u0E07: ", seg.arrive_time || "-", seg.arrive_plus ? ` ${seg.arrive_plus}` : ""), seg.aircraft_code && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07: ", getAircraftName(seg.aircraft_code)), seg.duration && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32: ", formatDuration(seg.duration)), layoverTime && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: {
        fontSize: "16px",
        color: "rgba(255, 215, 0, 0.95)",
        marginTop: "6px",
        padding: "4px 8px",
        background: "rgba(255, 215, 0, 0.2)",
        borderRadius: "4px",
        display: "inline-block",
        fontWeight: "500"
      } }, /* @__PURE__ */ import_react6.default.createElement("div", null, "\u23F1\uFE0F \u0E23\u0E2D\u0E04\u0E2D\u0E22\u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07: ", layoverTime), seg.to && /* @__PURE__ */ import_react6.default.createElement("div", { style: {
        fontSize: "14px",
        marginTop: "4px",
        opacity: 0.9
      } }, "\u0E17\u0E35\u0E48 ", getAirportDisplay(seg.to))));
    })) : /* @__PURE__ */ import_react6.default.createElement("div", null, "\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19 (\u0E41\u0E15\u0E48\u0E44\u0E21\u0E48\u0E1E\u0E1A segment)"), /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      marginTop: "16px",
      paddingTop: "12px",
      borderTop: "1px solid rgba(255, 255, 255, 0.25)"
    } }, (flightStops || flightCarriers) && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginBottom: "8px", fontSize: "16px", lineHeight: "1.6" } }, flightStops && /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "500" } }, flightStops), flightCarriers && /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "500" } }, " \u2022 ", flightCarriers)), (flight?.cabin || flight?.baggage || flight?.visa_warning) && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginBottom: "6px", fontSize: "16px", lineHeight: "1.6" } }, flight?.cabin && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "4px" } }, "\u0E0A\u0E31\u0E49\u0E19\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23: ", flight.cabin), flight?.baggage && /* @__PURE__ */ import_react6.default.createElement("div", null, "\u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32\u0E42\u0E2B\u0E25\u0E14: ", flight.baggage), flight?.visa_warning && /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      marginTop: "8px",
      padding: "10px 12px",
      background: "rgba(255, 77, 79, 0.15)",
      border: "1px solid rgba(255, 77, 79, 0.4)",
      borderRadius: "6px",
      color: "#ff4d4f",
      fontWeight: "600",
      fontSize: "15px",
      lineHeight: "1.5"
    } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", alignItems: "flex-start", gap: "8px", marginBottom: "4px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "18px" } }, "\u26A0\uFE0F"), /* @__PURE__ */ import_react6.default.createElement("div", { style: { flex: 1 } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "700", marginBottom: "4px" } }, "\u0E04\u0E33\u0E40\u0E15\u0E37\u0E2D\u0E19\u0E40\u0E23\u0E37\u0E48\u0E2D\u0E07\u0E27\u0E35\u0E0B\u0E48\u0E32 (Visa Warning)"), /* @__PURE__ */ import_react6.default.createElement("div", null, flight.visa_warning), /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      marginTop: "6px",
      fontSize: "13px",
      fontWeight: "400",
      color: "rgba(255, 77, 79, 0.9)",
      lineHeight: "1.4"
    } }, "\u{1F4A1} ", /* @__PURE__ */ import_react6.default.createElement("strong", null, "\u0E41\u0E19\u0E30\u0E19\u0E33:"), " \u0E01\u0E23\u0E38\u0E13\u0E32\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E04\u0E27\u0E32\u0E21\u0E15\u0E49\u0E2D\u0E07\u0E01\u0E32\u0E23\u0E27\u0E35\u0E0B\u0E48\u0E32\u0E2A\u0E33\u0E2B\u0E23\u0E31\u0E1A\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28\u0E1B\u0E25\u0E32\u0E22\u0E17\u0E32\u0E07\u0E41\u0E25\u0E30\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28\u0E17\u0E35\u0E48\u0E15\u0E49\u0E2D\u0E07\u0E1C\u0E48\u0E32\u0E19\u0E17\u0E32\u0E07 (Transit) \u0E01\u0E48\u0E2D\u0E19\u0E17\u0E33\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07 \u0E2B\u0E32\u0E01\u0E04\u0E38\u0E13\u0E21\u0E35\u0E27\u0E35\u0E0B\u0E48\u0E32\u0E17\u0E35\u0E48\u0E16\u0E39\u0E01\u0E15\u0E49\u0E2D\u0E07\u0E41\u0E25\u0E49\u0E27 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E2D\u0E31\u0E1E\u0E40\u0E14\u0E17\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E43\u0E19\u0E2B\u0E19\u0E49\u0E32\u0E42\u0E1B\u0E23\u0E44\u0E1F\u0E25\u0E4C")))), displayFlight?.segments && displayFlight.segments.length > 1 && /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      marginTop: "8px",
      padding: "10px 12px",
      background: "rgba(255, 193, 7, 0.15)",
      border: "1px solid rgba(255, 193, 7, 0.4)",
      borderRadius: "6px",
      fontSize: "14px",
      lineHeight: "1.5"
    } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", alignItems: "flex-start", gap: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "16px" } }, "\u2708\uFE0F"), /* @__PURE__ */ import_react6.default.createElement("div", { style: { flex: 1 } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "4px", color: "#f57c00" } }, "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E19\u0E35\u0E49\u0E21\u0E35\u0E01\u0E32\u0E23\u0E41\u0E27\u0E30\u0E23\u0E30\u0E2B\u0E27\u0E48\u0E32\u0E07\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontSize: "13px", color: "#e65100" } }, "\u2022 \u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E19\u0E35\u0E49\u0E21\u0E35 ", displayFlight.segments.length - 1, " \u0E08\u0E38\u0E14\u0E41\u0E27\u0E30 (Transit)", /* @__PURE__ */ import_react6.default.createElement("br", null), "\u2022 \u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E27\u0E48\u0E32\u0E04\u0E38\u0E13\u0E21\u0E35\u0E27\u0E35\u0E0B\u0E48\u0E32\u0E2A\u0E33\u0E2B\u0E23\u0E31\u0E1A\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28\u0E17\u0E35\u0E48\u0E15\u0E49\u0E2D\u0E07\u0E1C\u0E48\u0E32\u0E19\u0E17\u0E32\u0E07\u0E2B\u0E23\u0E37\u0E2D\u0E44\u0E21\u0E48", /* @__PURE__ */ import_react6.default.createElement("br", null), "\u2022 \u0E1A\u0E32\u0E07\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28\u0E2D\u0E32\u0E08\u0E15\u0E49\u0E2D\u0E07\u0E43\u0E0A\u0E49\u0E27\u0E35\u0E0B\u0E48\u0E32 Transit \u0E41\u0E21\u0E49\u0E44\u0E21\u0E48\u0E15\u0E49\u0E2D\u0E07\u0E2D\u0E2D\u0E01\u0E08\u0E32\u0E01\u0E2A\u0E19\u0E32\u0E21\u0E1A\u0E34\u0E19"))))), totalJourneyTime && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginBottom: "6px", fontWeight: "600", fontSize: "16px", lineHeight: "1.6" } }, "\u0E40\u0E27\u0E25\u0E32\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14: ", totalJourneyTime), flightPrice && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginTop: "6px", fontWeight: "600", fontSize: "16px", lineHeight: "1.6" } }, "\u0E23\u0E32\u0E04\u0E32\u0E23\u0E27\u0E21: ", flightPrice)), !display_text && /* @__PURE__ */ import_react6.default.createElement(
      "button",
      {
        onClick: () => setShowFlightDetails(!showFlightDetails),
        style: {
          marginTop: "8px",
          padding: "6px 12px",
          background: "rgba(255, 255, 255, 0.15)",
          border: "1px solid rgba(255, 255, 255, 0.3)",
          borderRadius: "6px",
          color: "#ffffff",
          fontSize: "14px",
          cursor: "pointer",
          fontWeight: "600",
          transition: "all 0.2s"
        },
        onMouseOver: (e) => {
          e.target.style.background = "rgba(255, 255, 255, 0.25)";
        },
        onMouseOut: (e) => {
          e.target.style.background = "rgba(255, 255, 255, 0.15)";
        }
      },
      showFlightDetails ? "\u25BC \u0E0B\u0E48\u0E2D\u0E19\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14" : "\u25B6 \u0E14\u0E39\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E40\u0E15\u0E34\u0E21"
    ), !display_text && showFlightDetails && flight_details && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "12px", padding: "12px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "8px", fontSize: "16px" } }, "1) \u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07 & \u0E40\u0E27\u0E25\u0E32"), displayFlight.segments && displayFlight.segments.map((seg, idx) => /* @__PURE__ */ import_react6.default.createElement("div", { key: idx, style: { marginBottom: "8px", paddingLeft: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E2A\u0E32\u0E22\u0E01\u0E32\u0E23\u0E1A\u0E34\u0E19: ", getAirlineName(seg.carrier)), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E25\u0E02\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19: ", seg.carrier && seg.flight_number ? `${seg.carrier}${seg.flight_number}` : seg.flight_number || "-"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E15\u0E49\u0E19\u0E17\u0E32\u0E07 \u2192 \u0E1B\u0E25\u0E32\u0E22\u0E17\u0E32\u0E07: ", seg.from || "-", " \u2192 ", seg.to || "-"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E27\u0E31\u0E19\u2013\u0E40\u0E27\u0E25\u0E32\u0E2D\u0E2D\u0E01: ", seg.depart_at ? new Date(seg.depart_at).toLocaleString("th-TH") : seg.depart_time || "-"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E27\u0E31\u0E19\u2013\u0E40\u0E27\u0E25\u0E32\u0E16\u0E36\u0E07: ", seg.arrive_at ? new Date(seg.arrive_at).toLocaleString("th-TH") : seg.arrive_time || "-", seg.arrive_plus || ""), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32\u0E1A\u0E34\u0E19: ", formatDuration(seg.duration)))), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginTop: "4px" } }, flightStops === "Non-stop" ? "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07" : `${flightStops} (\u0E41\u0E27\u0E30 ${flight?.segments?.length - 1 || 0} \u0E04\u0E23\u0E31\u0E49\u0E07)`)), /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "8px", fontSize: "16px" } }, "2) \u0E23\u0E32\u0E04\u0E32 & \u0E40\u0E07\u0E37\u0E48\u0E2D\u0E19\u0E44\u0E02"), flightPrice && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E23\u0E32\u0E04\u0E32\u0E23\u0E27\u0E21: ", flightPrice), flight?.currency && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E2A\u0E01\u0E38\u0E25\u0E40\u0E07\u0E34\u0E19: ", flight.currency), flight_details?.price_per_person && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E48\u0E2D\u0E04\u0E19: ", flight_details.price_per_person.toLocaleString("th-TH"), " ", flight?.currency || "THB"), flight?.cabin && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E0A\u0E31\u0E49\u0E19\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23: ", flight.cabin), /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "6px" } }, "\u{1F4CB} Fare Rules"), /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", gap: "8px", flexWrap: "wrap" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: {
      padding: "4px 8px",
      borderRadius: "4px",
      fontSize: "13px",
      fontWeight: "500",
      backgroundColor: flight_details?.refundable ? "rgba(74, 222, 128, 0.2)" : "rgba(248, 113, 113, 0.2)",
      color: flight_details?.refundable ? "#4ade80" : "#f87171",
      border: `1px solid ${flight_details?.refundable ? "rgba(74, 222, 128, 0.4)" : "rgba(248, 113, 113, 0.4)"}`
    } }, "Refundable: ", flight_details?.refundable ? "\u2705 \u0E04\u0E37\u0E19\u0E40\u0E07\u0E34\u0E19\u0E44\u0E14\u0E49" : "\u274C \u0E04\u0E37\u0E19\u0E40\u0E07\u0E34\u0E19\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49"), /* @__PURE__ */ import_react6.default.createElement("span", { style: {
      padding: "4px 8px",
      borderRadius: "4px",
      fontSize: "13px",
      fontWeight: "500",
      backgroundColor: flight_details?.changeable ? "rgba(96, 165, 250, 0.2)" : "rgba(248, 113, 113, 0.2)",
      color: flight_details?.changeable ? "#60a5fa" : "#f87171",
      border: `1px solid ${flight_details?.changeable ? "rgba(96, 165, 250, 0.4)" : "rgba(248, 113, 113, 0.4)"}`
    } }, "Changeable: ", flight_details?.changeable ? "\u2705 \u0E40\u0E25\u0E37\u0E48\u0E2D\u0E19\u0E27\u0E31\u0E19\u0E44\u0E14\u0E49" : "\u274C \u0E40\u0E25\u0E37\u0E48\u0E2D\u0E19\u0E27\u0E31\u0E19\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49"), flight_details?.changeable && flight_details?.change_fee && /* @__PURE__ */ import_react6.default.createElement("span", { className: "plan-card-small", style: { display: "block", marginTop: "4px" } }, "\u0E04\u0E48\u0E32\u0E18\u0E23\u0E23\u0E21\u0E40\u0E19\u0E35\u0E22\u0E21: ", flight_details.change_fee)), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginTop: "4px", fontSize: "12px", opacity: 0.8 } }, "*\u0E40\u0E07\u0E37\u0E48\u0E2D\u0E19\u0E44\u0E02\u0E40\u0E1B\u0E47\u0E19\u0E44\u0E1B\u0E15\u0E32\u0E21\u0E17\u0E35\u0E48\u0E2A\u0E32\u0E22\u0E01\u0E32\u0E23\u0E1A\u0E34\u0E19\u0E01\u0E33\u0E2B\u0E19\u0E14 \u0E2D\u0E32\u0E08\u0E21\u0E35\u0E04\u0E48\u0E32\u0E18\u0E23\u0E23\u0E21\u0E40\u0E19\u0E35\u0E22\u0E21\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E40\u0E15\u0E34\u0E21"))), /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "8px", fontSize: "16px" } }, "\u{1F9F3} Baggage Allowance"), /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { display: "flex", alignItems: "center", gap: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F45C}"), /* @__PURE__ */ import_react6.default.createElement("span", null, "\u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32\u0E16\u0E37\u0E2D\u0E02\u0E36\u0E49\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07: ", flight_details?.hand_baggage || "1 \u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32 (7 kg)")), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { display: "flex", alignItems: "center", gap: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F9F3}"), /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600", color: "#ffecb3" } }, "\u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32\u0E42\u0E2B\u0E25\u0E14: ", flight?.baggage || flight_details?.checked_baggage || "\u0E44\u0E21\u0E48\u0E23\u0E27\u0E21")))), /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "8px", fontSize: "16px" } }, "\u2728 \u0E2A\u0E34\u0E48\u0E07\u0E2D\u0E33\u0E19\u0E27\u0E22\u0E04\u0E27\u0E32\u0E21\u0E2A\u0E30\u0E14\u0E27\u0E01"), /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { display: "flex", alignItems: "center", gap: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F4F6}"), /* @__PURE__ */ import_react6.default.createElement("span", null, "WiFi: ", flight_details?.wifi ?? "\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E1A\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07")), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { display: "flex", alignItems: "center", gap: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F50C}"), /* @__PURE__ */ import_react6.default.createElement("span", null, "\u0E1B\u0E25\u0E31\u0E4A\u0E01\u0E44\u0E1F: ", flight_details?.power_outlet ?? "\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E1A\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07")), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { display: "flex", alignItems: "center", gap: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F37D}\uFE0F"), /* @__PURE__ */ import_react6.default.createElement("span", null, "\u0E2D\u0E32\u0E2B\u0E32\u0E23: ", flight_details?.meals || "\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E27\u0E48\u0E32\u0E07")), (flight_details?.seat_width || flight_details?.seat_selection) && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { display: "flex", alignItems: "center", gap: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F4BA}"), /* @__PURE__ */ import_react6.default.createElement("span", null, "\u0E04\u0E27\u0E32\u0E21\u0E01\u0E27\u0E49\u0E32\u0E07\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07: ", flight_details?.seat_width || flight_details?.seat_selection)))), (() => {
      const route = displayFlight?.segments?.length ? displayFlight.segments[0]?.from && displayFlight.segments[displayFlight.segments.length - 1]?.to : false;
      const co2Kg = flight_details?.co2_emissions_kg ?? (route ? calculateCO2e(1500) : null);
      return co2Kg != null && co2Kg > 0 ? /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "4px" } }, "\u{1F331} CO2 Emissions"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "~", co2Kg, " kg CO2e (\u0E1B\u0E23\u0E30\u0E21\u0E32\u0E13\u0E01\u0E32\u0E23)")) : null;
    })(), flight_details?.on_time_performance != null && flight_details.on_time_performance !== "" && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "4px" } }, "\u23F1\uFE0F On-time Performance"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, flight_details.on_time_performance)), flight_details?.promotions && flight_details.promotions.length > 0 && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "8px", fontSize: "16px" } }, "\u{1F381} \u0E42\u0E1B\u0E23\u0E42\u0E21\u0E0A\u0E31\u0E48\u0E19"), flight_details.promotions.map((promo, idx) => /* @__PURE__ */ import_react6.default.createElement("div", { key: idx, style: { marginBottom: "8px", padding: "8px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { fontWeight: "600" } }, "\u0E0A\u0E37\u0E48\u0E2D\u0E42\u0E1B\u0E23\u0E42\u0E21\u0E0A\u0E31\u0E48\u0E19: ", promo.name), promo.type && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E42\u0E1B\u0E23\u0E42\u0E21\u0E0A\u0E31\u0E48\u0E19: ", promo.type), promo.discount && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E25\u0E14\u0E23\u0E32\u0E04\u0E32: ", promo.discount), promo.code && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E42\u0E04\u0E49\u0E14\u0E2A\u0E48\u0E27\u0E19\u0E25\u0E14: ", promo.code), promo.extra_baggage && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E41\u0E16\u0E21\u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32: ", promo.extra_baggage), promo.seat_upgrade && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E2D\u0E31\u0E1B\u0E40\u0E01\u0E23\u0E14\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07: ", promo.seat_upgrade), promo.benefit && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E08\u0E33\u0E19\u0E27\u0E19\u0E40\u0E07\u0E34\u0E19\u0E17\u0E35\u0E48\u0E25\u0E14 / \u0E2A\u0E34\u0E17\u0E18\u0E34\u0E4C\u0E17\u0E35\u0E48\u0E44\u0E14\u0E49: ", promo.benefit), promo.conditions && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E07\u0E37\u0E48\u0E2D\u0E19\u0E44\u0E02\u0E01\u0E32\u0E23\u0E43\u0E0A\u0E49: ", promo.conditions), promo.expiry && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E27\u0E31\u0E19\u0E2B\u0E21\u0E14\u0E2D\u0E32\u0E22\u0E38: ", promo.expiry), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { fontWeight: "600", color: promo.applicable ? "#4ade80" : "#ef4444" } }, "\u0E43\u0E0A\u0E49\u0E44\u0E14\u0E49\u0E01\u0E31\u0E1A\u0E44\u0E1F\u0E17\u0E4C\u0E19\u0E35\u0E49\u0E2B\u0E23\u0E37\u0E2D\u0E44\u0E21\u0E48: ", promo.applicable ? "\u2705 \u0E43\u0E0A\u0E49\u0E44\u0E14\u0E49" : "\u274C \u0E43\u0E0A\u0E49\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49"))))))), hotel && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F3E8} \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01: ", hotel.hotelName || hotel.name || "Unknown Hotel"), hotel.visuals?.image_urls && hotel.visuals.image_urls.length > 0 && /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      width: "100%",
      overflowX: "auto",
      whiteSpace: "nowrap",
      marginBottom: "12px",
      borderRadius: "8px",
      scrollbarWidth: "none"
    } }, hotel.visuals.image_urls.map((url, idx) => /* @__PURE__ */ import_react6.default.createElement(
      "img",
      {
        key: idx,
        src: url,
        alt: "",
        loading: "lazy",
        onError: (e) => {
          e.target.style.display = "none";
        },
        style: {
          width: "120px",
          height: "80px",
          objectFit: "cover",
          borderRadius: "6px",
          marginRight: "8px",
          display: "inline-block"
        }
      }
    ))), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-body" }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" } }, hotel.star_rating && /* @__PURE__ */ import_react6.default.createElement("span", { style: { color: "#FFD700", fontSize: "14px" } }, "\u2B50".repeat(Math.round(hotel.star_rating)), " (", hotel.star_rating, ")"), hotel.visuals?.review_score && /* @__PURE__ */ import_react6.default.createElement("span", { style: {
      fontSize: "12px",
      background: "#4CAF50",
      color: "white",
      padding: "2px 6px",
      borderRadius: "4px"
    } }, hotel.visuals.review_score, " / 5 (", hotel.visuals.review_count || 0, " \u0E23\u0E35\u0E27\u0E34\u0E27)")), hotel.location?.address && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginBottom: "8px", opacity: 0.9 } }, "\u{1F4CD} ", hotel.location.address), hotel.amenities && /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      display: "flex",
      gap: "12px",
      marginBottom: "12px",
      padding: "8px",
      background: "rgba(255,255,255,0.1)",
      borderRadius: "6px",
      fontSize: "18px"
    } }, hotel.amenities.has_wifi && /* @__PURE__ */ import_react6.default.createElement("span", { title: "Free Wi-Fi" }, "\u{1F4F6}"), hotel.amenities.has_pool && /* @__PURE__ */ import_react6.default.createElement("span", { title: "Swimming Pool" }, "\u{1F3CA}"), hotel.amenities.has_fitness && /* @__PURE__ */ import_react6.default.createElement("span", { title: "Fitness Center" }, "\u{1F3CB}\uFE0F"), hotel.amenities.has_parking && /* @__PURE__ */ import_react6.default.createElement("span", { title: "Parking" }, "\u{1F17F}\uFE0F"), hotel.amenities.has_spa && /* @__PURE__ */ import_react6.default.createElement("span", { title: "Spa" }, "\u{1F486}"), hotel.amenities.has_air_conditioning && /* @__PURE__ */ import_react6.default.createElement("span", { title: "Air Con" }, "\u2744\uFE0F")), /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", paddingLeft: "8px", borderLeft: "3px solid rgba(255,255,255,0.3)" } }, hotel.booking?.room?.room_type && /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", fontSize: "15px" } }, "\u{1F6CF}\uFE0F ", hotel.booking.room.room_type), hotel.booking?.room?.bed_type && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, hotel.booking.room.bed_quantity, " x ", hotel.booking.room.bed_type), hotel.booking?.policies?.meal_plan && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u{1F37D}\uFE0F ", hotel.booking.policies.meal_plan), /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "6px", display: "flex", gap: "6px" } }, hotel.booking?.policies && /* @__PURE__ */ import_react6.default.createElement("span", { style: {
      padding: "2px 6px",
      borderRadius: "4px",
      fontSize: "11px",
      fontWeight: "600",
      backgroundColor: hotel.booking.policies.is_refundable ? "rgba(74, 222, 128, 0.2)" : "rgba(248, 113, 113, 0.2)",
      color: hotel.booking.policies.is_refundable ? "#4ade80" : "#f87171",
      border: `1px solid ${hotel.booking.policies.is_refundable ? "rgba(74, 222, 128, 0.4)" : "rgba(248, 113, 113, 0.4)"}`
    } }, hotel.booking.policies.is_refundable ? "\u2705 \u0E22\u0E01\u0E40\u0E25\u0E34\u0E01\u0E1F\u0E23\u0E35" : "\u274C \u0E2B\u0E49\u0E32\u0E21\u0E22\u0E01\u0E40\u0E25\u0E34\u0E01"))), (hotel.booking?.pricing || hotelTotalAmount != null) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "8px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.2)" } }, hotelPricePerNight != null && /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "13px", opacity: 0.8 } }, "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E48\u0E2D\u0E04\u0E37\u0E19"), /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, formatPriceInThb(hotelPricePerNight, hotelPricingCurrency))), hotelTaxesAndFees != null && /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "13px", opacity: 0.8 } }, "\u0E20\u0E32\u0E29\u0E35\u0E41\u0E25\u0E30\u0E04\u0E48\u0E32\u0E18\u0E23\u0E23\u0E21\u0E40\u0E19\u0E35\u0E22\u0E21"), /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontSize: "13px" } }, formatPriceInThb(hotelTaxesAndFees, hotelPricingCurrency))), hotelTotalAmount != null && /* @__PURE__ */ import_react6.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px", fontSize: "16px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u0E23\u0E32\u0E04\u0E32\u0E23\u0E27\u0E21\u0E08\u0E32\u0E01 Amadeus"), /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "700", color: "#81c784" } }, formatPriceInThb(hotelTotalAmount, hotelPricingCurrency)))), !hotel.booking && /* @__PURE__ */ import_react6.default.createElement(import_react6.default.Fragment, null, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "500" } }, hotelName || "Unknown Hotel"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, hotelNights != null ? `\u0E08\u0E33\u0E19\u0E27\u0E19\u0E04\u0E37\u0E19: ${hotelNights}` : "", hotelBoard ? ` \u2022 \u0E41\u0E1E\u0E47\u0E01\u0E40\u0E01\u0E08: ${hotelBoard}` : ""), hotel?.address && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small" }, "\u0E17\u0E35\u0E48\u0E2D\u0E22\u0E39\u0E48: ", hotel.address), hotelPrice && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-small", style: { marginTop: "4px", fontWeight: "500" } }, "\u0E23\u0E32\u0E04\u0E32: ", hotelPrice, " (\u0E15\u0E32\u0E21 Amadeus)")))), ground_transport && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F697} \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, typeof ground_transport === "string" ? ground_transport.split("\n").map((line, idx) => /* @__PURE__ */ import_react6.default.createElement("div", { key: idx }, line)) : /* @__PURE__ */ import_react6.default.createElement("div", null, ground_transport.description && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "12px", fontSize: "15px", lineHeight: "1.6" } }, ground_transport.description)))), (transport || car) && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-title" }, transport?.type === "car_rental" || car ? "\u{1F697} \u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32" : transport?.type === "bus" ? "\u{1F68C} \u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23" : transport?.type === "train" ? "\u{1F682} \u0E23\u0E16\u0E44\u0E1F" : transport?.type === "metro" ? "\u{1F687} \u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32" : transport?.type === "ferry" ? "\u26F4\uFE0F \u0E40\u0E23\u0E37\u0E2D" : "\u{1F697} \u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, transport?.type && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "8px", fontSize: "16px", fontWeight: "600" } }, "\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17: ", transport.type === "car_rental" ? "\u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32" : transport.type === "bus" ? "\u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23" : transport.type === "train" ? "\u0E23\u0E16\u0E44\u0E1F" : transport.type === "metro" ? "\u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32" : transport.type === "ferry" ? "\u0E40\u0E23\u0E37\u0E2D" : transport.type === "transfer" ? "\u0E23\u0E16\u0E23\u0E31\u0E1A\u0E2A\u0E48\u0E07" : transport.type), (transport?.route || transport?.data?.route || car?.route) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "8px", fontSize: "15px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07: "), transport?.route || transport?.data?.route || car?.route), (transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount) && /* @__PURE__ */ import_react6.default.createElement("div", { style: {
      marginBottom: "12px",
      padding: "12px",
      background: "rgba(74, 222, 128, 0.15)",
      borderRadius: "8px",
      border: "1px solid rgba(74, 222, 128, 0.3)"
    } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontSize: "18px", fontWeight: "700", color: "#4ade80", marginBottom: "4px" } }, "\u{1F4B0} \u0E23\u0E32\u0E04\u0E32: ", formatPriceInThb(
      transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount,
      transport?.currency || transport?.data?.currency || car?.currency || "THB"
    )), (transport?.price_per_day || car?.price_per_day) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontSize: "14px", opacity: 0.9, marginTop: "4px" } }, "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E48\u0E2D\u0E27\u0E31\u0E19: ", formatPriceInThb(
      transport?.price_per_day || car?.price_per_day,
      transport?.currency || car?.currency || "THB"
    ))), (transport?.duration || transport?.data?.duration || car?.duration) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "8px", fontSize: "15px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u23F1\uFE0F \u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32: "), formatDuration(transport?.duration || transport?.data?.duration || car?.duration) || (transport?.duration || transport?.data?.duration || car?.duration)), (transport?.distance || transport?.data?.distance || car?.distance) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "8px", fontSize: "15px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u{1F4CF} \u0E23\u0E30\u0E22\u0E30\u0E17\u0E32\u0E07: "), typeof (transport?.distance || transport?.data?.distance || car?.distance) === "number" ? `${(transport?.distance || transport?.data?.distance || car?.distance).toLocaleString("th-TH")} \u0E01\u0E21.` : transport?.distance || transport?.data?.distance || car?.distance), (transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "8px", fontSize: "15px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u{1F3E2} \u0E1A\u0E23\u0E34\u0E29\u0E31\u0E17: "), transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company), (transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "8px", fontSize: "15px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u{1F699} \u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E23\u0E16: "), transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type), (transport?.seats || car?.seats || transport?.capacity || car?.capacity) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginBottom: "8px", fontSize: "15px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u{1F4BA} \u0E08\u0E33\u0E19\u0E27\u0E19\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07: "), transport?.seats || car?.seats || transport?.capacity || car?.capacity, " \u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07"), (transport?.details || transport?.data?.details || car?.details) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "12px", padding: "10px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "6px" } }, "\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E40\u0E15\u0E34\u0E21:"), Array.isArray(transport?.details || transport?.data?.details || car?.details) ? (transport?.details || transport?.data?.details || car?.details).map((detail, idx) => /* @__PURE__ */ import_react6.default.createElement("div", { key: idx, style: { marginBottom: "4px" } }, "\u2022 ", detail)) : /* @__PURE__ */ import_react6.default.createElement("div", null, transport?.details || transport?.data?.details || car?.details)), (transport?.features || car?.features || transport?.amenities || car?.amenities) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "12px", padding: "10px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "6px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "600", marginBottom: "6px" } }, "\u0E04\u0E38\u0E13\u0E2A\u0E21\u0E1A\u0E31\u0E15\u0E34:"), Array.isArray(transport?.features || car?.features || transport?.amenities || car?.amenities) ? (transport?.features || car?.features || transport?.amenities || car?.amenities).map((feature, idx) => /* @__PURE__ */ import_react6.default.createElement("div", { key: idx, style: { marginBottom: "4px" } }, "\u2713 ", feature)) : /* @__PURE__ */ import_react6.default.createElement("div", null, transport?.features || car?.features || transport?.amenities || car?.amenities)), (transport?.note || transport?.data?.note || car?.note) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginTop: "12px", padding: "10px", background: "rgba(255, 193, 7, 0.15)", borderRadius: "6px", fontSize: "14px" } }, /* @__PURE__ */ import_react6.default.createElement("span", { style: { fontWeight: "600" } }, "\u{1F4DD} \u0E2B\u0E21\u0E32\u0E22\u0E40\u0E2B\u0E15\u0E38: "), transport?.note || transport?.data?.note || car?.note))), itinerary && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-title", style: { display: "flex", justifyContent: "space-between", alignItems: "center" } }, /* @__PURE__ */ import_react6.default.createElement("span", null, "\u{1F4C5} Day-by-Day Itinerary"), /* @__PURE__ */ import_react6.default.createElement(
      "button",
      {
        onClick: () => setShowItinerary(!showItinerary),
        style: {
          background: "transparent",
          border: "1px solid rgba(0,0,0,0.2)",
          borderRadius: "4px",
          padding: "4px 12px",
          fontSize: "11px",
          cursor: "pointer",
          color: "#666",
          transition: "all 0.2s"
        },
        onMouseOver: (e) => {
          e.target.style.background = "rgba(0,0,0,0.05)";
          e.target.style.borderColor = "rgba(0,0,0,0.3)";
        },
        onMouseOut: (e) => {
          e.target.style.background = "transparent";
          e.target.style.borderColor = "rgba(0,0,0,0.2)";
        }
      },
      showItinerary ? "\u25BC \u0E0B\u0E48\u0E2D\u0E19" : "\u25B6 \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E40\u0E15\u0E34\u0E21"
    )), showItinerary && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-body plan-card-small", style: { marginTop: "8px" } }, typeof itinerary === "string" ? (
      // If itinerary is a string (like day trip)
      /* @__PURE__ */ import_react6.default.createElement("div", { style: { whiteSpace: "pre-line" } }, itinerary)
    ) : Array.isArray(itinerary) ? (
      // If itinerary is an array of days
      itinerary.map((day, idx) => /* @__PURE__ */ import_react6.default.createElement("div", { key: idx, style: { marginBottom: "8px" } }, /* @__PURE__ */ import_react6.default.createElement("div", { style: { fontWeight: "500" } }, "\u{1F5D3} Day ", day.day || idx + 1, " \u2013 ", day.title || "Day " + (idx + 1)), day.items && Array.isArray(day.items) && /* @__PURE__ */ import_react6.default.createElement("div", { style: { marginLeft: "12px", marginTop: "4px" } }, day.items.map((item, itemIdx) => /* @__PURE__ */ import_react6.default.createElement("div", { key: itemIdx }, "- ", item)))))
    ) : null)), transport && !ground_transport && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F697} \u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, transportMode && /* @__PURE__ */ import_react6.default.createElement("div", null, transportMode), transportNote && /* @__PURE__ */ import_react6.default.createElement("div", null, transportNote), !transportMode && !transportNote && /* @__PURE__ */ import_react6.default.createElement("div", null, "\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"))), price_breakdown && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section plan-card-price-breakdown" }, /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F4B0} \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E23\u0E32\u0E04\u0E32"), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, breakdownFlight && /* @__PURE__ */ import_react6.default.createElement("div", null, "\u2708\uFE0F \u0E15\u0E31\u0E4B\u0E27\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07\u0E1A\u0E34\u0E19: ", breakdownFlight), breakdownHotel && /* @__PURE__ */ import_react6.default.createElement("div", null, "\u{1F3E8} \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01: ", breakdownHotel), breakdownTransport && /* @__PURE__ */ import_react6.default.createElement("div", null, transportType === "car_rental" ? "\u{1F697} \u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32" : transportType === "bus" ? "\u{1F68C} \u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23" : transportType === "train" ? "\u{1F682} \u0E23\u0E16\u0E44\u0E1F" : transportType === "metro" ? "\u{1F687} \u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32" : transportType === "ferry" ? "\u26F4\uFE0F \u0E40\u0E23\u0E37\u0E2D" : "\u{1F697} \u0E23\u0E16\u0E41\u0E25\u0E30\u0E40\u0E23\u0E37\u0E2D", ": ", breakdownTransport), !breakdownFlight && !breakdownHotel && !breakdownTransport && /* @__PURE__ */ import_react6.default.createElement("div", null, "\u0E44\u0E21\u0E48\u0E21\u0E35\u0E23\u0E32\u0E22\u0E01\u0E32\u0E23\u0E41\u0E22\u0E01\u0E23\u0E32\u0E04\u0E32\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E40\u0E15\u0E34\u0E21"))), /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-footer" }, displayTotalPrice && /* @__PURE__ */ import_react6.default.createElement("div", { className: "plan-card-price" }, displayTotalPrice), /* @__PURE__ */ import_react6.default.createElement(
      "button",
      {
        className: "plan-card-button",
        onClick: () => onSelect && onSelect(id)
      },
      "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ",
      id
    )));
  }

  // src/components/bookings/PlanChoiceCardFlights.jsx
  var import_react7 = __toESM(require_react(), 1);

  // src/components/bookings/planChoiceCardUtils.js
  function formatMoney(value, currency = "THB") {
    return formatPriceInThb(value, currency);
  }
  function formatDuration2(durationStr) {
    if (!durationStr || typeof durationStr !== "string") return "";
    if (durationStr.startsWith("PT")) {
      let hours = 0;
      let minutes = 0;
      try {
        if (durationStr.includes("H")) {
          const hoursPart = durationStr.split("H")[0].replace("PT", "");
          hours = parseInt(hoursPart) || 0;
          const remaining = durationStr.split("H")[1] || "";
          if (remaining.includes("M")) {
            const minutesPart = remaining.split("M")[0];
            minutes = parseInt(minutesPart) || 0;
          }
        } else {
          const remaining = durationStr.replace("PT", "");
          if (remaining.includes("M")) {
            const minutesPart = remaining.split("M")[0];
            minutes = parseInt(minutesPart) || 0;
          }
        }
        const parts = [];
        if (hours > 0) parts.push(`${hours}\u0E0A\u0E21`);
        if (minutes > 0) parts.push(`${minutes}\u0E19\u0E32\u0E17\u0E35`);
        return parts.length > 0 ? parts.join(" ") : "\u0E44\u0E21\u0E48\u0E23\u0E30\u0E1A\u0E38";
      } catch (e) {
        return durationStr;
      }
    }
    return durationStr;
  }
  function parseDurationToHours(durationStr) {
    if (!durationStr || typeof durationStr !== "string") return 0;
    if (!durationStr.startsWith("PT")) return 0;
    try {
      let hours = 0;
      let minutes = 0;
      if (durationStr.includes("H")) {
        const hoursPart = durationStr.split("H")[0].replace("PT", "");
        hours = parseInt(hoursPart, 10) || 0;
        const remaining = durationStr.split("H")[1] || "";
        if (remaining.includes("M")) minutes = parseInt(remaining.split("M")[0], 10) || 0;
      } else if (durationStr.includes("M")) {
        minutes = parseInt(durationStr.replace(/^PT|M.*$/g, ""), 10) || 0;
      }
      return hours + minutes / 60;
    } catch (e) {
      return 0;
    }
  }
  function calculateCO2e2(distanceKm) {
    if (!distanceKm || distanceKm <= 0) return 0;
    return Math.round(distanceKm * 0.22);
  }

  // src/utils/flightSegments.js
  function normalizeDepartureKey(dep) {
    if (dep == null || dep === "") return "";
    const s = String(dep).trim();
    if (!s) return "";
    try {
      let normalized = s;
      const thaiDateMatch = s.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s*(\d{1,2}:\d{2}(?::\d{2})?)?/);
      if (thaiDateMatch) {
        const [, day, month, y, time = "00:00:00"] = thaiDateMatch;
        const year = parseInt(y, 10);
        const budYear = year > 2500 ? year - 543 : year;
        const t = time.length <= 5 ? `${time}:00` : time;
        normalized = `${budYear}-${month.padStart(2, "0")}-${day.padStart(2, "0")}T${t.padEnd(8, "0").slice(0, 8)}`;
      }
      const d = new Date(normalized);
      if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 19);
    } catch (_) {
    }
    return s.slice(0, 19);
  }
  function segmentDedupKey(seg) {
    if (!seg || typeof seg !== "object") return "";
    const from = (seg.from ?? "").toString().trim().toUpperCase();
    const to = (seg.to ?? "").toString().trim().toUpperCase();
    const dep = seg.depart_at ?? seg.departure ?? "";
    const depStr = normalizeDepartureKey(dep != null ? String(dep) : "");
    const carrier = (seg.carrier ?? "").toString().trim().toUpperCase();
    const num = (seg.number ?? seg.flight_number ?? "").toString().trim();
    return `${from}-${to}-${depStr}-${carrier}-${num}`;
  }
  function dedupeSegments(segments) {
    if (!Array.isArray(segments) || segments.length === 0) return segments;
    const seen = /* @__PURE__ */ new Set();
    return segments.filter((seg) => {
      const key = segmentDedupKey(seg);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  // src/components/bookings/PlanChoiceCardFlights.jsx
  function calculateLayoverTime2(prevSegment, nextSegment) {
    if (!prevSegment || !nextSegment) return null;
    const prevArrival = prevSegment.arrive_at || prevSegment.depart_at;
    const nextDeparture = nextSegment.depart_at || nextSegment.depart_at;
    if (!prevArrival || !nextDeparture) return null;
    try {
      const diffMs = new Date(nextDeparture).getTime() - new Date(prevArrival).getTime();
      const diffHours = Math.floor(diffMs / (1e3 * 60 * 60));
      const diffMinutes = Math.floor(diffMs % (1e3 * 60 * 60) / (1e3 * 60));
      if (diffHours < 0 || diffMinutes < 0) return null;
      return diffHours > 0 ? `${diffHours}\u0E0A\u0E21 ${diffMinutes}\u0E19\u0E32\u0E17\u0E35` : `${diffMinutes}\u0E19\u0E32\u0E17\u0E35`;
    } catch (e) {
      return null;
    }
  }
  var getDuffelLogoUrl2 = (code) => {
    const c = String(code || "").toUpperCase();
    if (!c || c.length !== 2) return null;
    return `https://assets.duffel.com/img/airlines/for-light-background/full-color-logo/${c}.svg`;
  };
  var getKiwiLogoUrl2 = (code) => `https://images.kiwi.com/airlines/64/${String(code).toUpperCase()}.png`;
  var getClearbitLogoUrl2 = (code) => {
    const domain = AIRLINE_DOMAINS[String(code).toUpperCase()];
    return domain ? `https://logo.clearbit.com/${domain}` : null;
  };
  var getGoogleFaviconUrl2 = (code) => {
    const domain = AIRLINE_DOMAINS[String(code).toUpperCase()];
    return domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=64` : null;
  };
  function AirlineLogo2({ carrierCode, size = 40 }) {
    const [showFallback, setShowFallback] = (0, import_react7.useState)(false);
    const kiwiUrl = getKiwiLogoUrl2(carrierCode);
    const duffelUrl = getDuffelLogoUrl2(carrierCode);
    const clearbitUrl = getClearbitLogoUrl2(carrierCode);
    const googleFaviconUrl = getGoogleFaviconUrl2(carrierCode);
    const initialSrc = duffelUrl || kiwiUrl;
    const handleError = (e) => {
      const img = e.target;
      const src = (img.src || "").toLowerCase();
      const isDuffel = src.includes("assets.duffel.com");
      const isKiwi = src.includes("images.kiwi.com");
      const isClearbit = src.includes("logo.clearbit.com");
      if (isDuffel && kiwiUrl) {
        img.src = kiwiUrl;
        return;
      }
      if (isKiwi && clearbitUrl) {
        img.src = clearbitUrl;
        return;
      }
      if (isClearbit && googleFaviconUrl) {
        img.src = googleFaviconUrl;
        return;
      }
      setShowFallback(true);
      img.style.display = "none";
    };
    if (!carrierCode || showFallback || !initialSrc) {
      return /* @__PURE__ */ import_react7.default.createElement("div", { style: { width: size, height: size, borderRadius: 6, background: "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: Math.max(10, size * 0.3), fontWeight: 600, color: "#fff" } }, "\u2708\uFE0F ", carrierCode || "N/A");
    }
    return /* @__PURE__ */ import_react7.default.createElement(import_react7.default.Fragment, null, /* @__PURE__ */ import_react7.default.createElement(
      "img",
      {
        src: initialSrc,
        alt: carrierCode,
        style: { width: size, height: size, borderRadius: 6, objectFit: "contain", display: showFallback ? "none" : "block" },
        onError: handleError
      }
    ));
  }
  function getAirlineName2(code) {
    if (!code) return "Unknown";
    return AIRLINE_NAMES[String(code).toUpperCase()] || code;
  }
  function getAircraftName2(code) {
    if (!code) return "";
    const names = {
      "738": "Boeing 737-800",
      "739": "Boeing 737-900",
      "73H": "Boeing 737-800",
      "73J": "Boeing 737 MAX 8",
      "320": "Airbus A320",
      "321": "Airbus A321",
      "333": "Airbus A330-300",
      "77W": "Boeing 777-300ER",
      "788": "Boeing 787-8",
      "789": "Boeing 787-9"
    };
    return names[String(code).toUpperCase()] || `\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07\u0E1A\u0E34\u0E19 ${code}`;
  }
  function getFlightType2(segments) {
    if (!segments || segments.length === 0) return "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07";
    return segments.length > 1 ? "\u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07" : "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07";
  }
  function getCabinDisplay(cabin) {
    if (!cabin) return null;
    const c = String(cabin).toUpperCase();
    const map = {
      ECONOMY: "\u0E0A\u0E31\u0E49\u0E19\u0E1B\u0E23\u0E30\u0E2B\u0E22\u0E31\u0E14",
      PREMIUM_ECONOMY: "\u0E0A\u0E31\u0E49\u0E19\u0E1B\u0E23\u0E30\u0E2B\u0E22\u0E31\u0E14\u0E1E\u0E23\u0E35\u0E40\u0E21\u0E35\u0E22\u0E21",
      BUSINESS: "\u0E0A\u0E31\u0E49\u0E19\u0E18\u0E38\u0E23\u0E01\u0E34\u0E08",
      FIRST: "\u0E0A\u0E31\u0E49\u0E19\u0E2B\u0E19\u0E36\u0E48\u0E07"
    };
    return map[c] || cabin;
  }
  function getArrivalTimeDisplay2(arriveAt, arrivePlus) {
    if (!arriveAt) return "";
    let timeStr = typeof arriveAt === "string" && arriveAt.includes("T") ? arriveAt.split("T")[1]?.slice(0, 5) || "" : arriveAt || "";
    return arrivePlus ? `${timeStr} ${arrivePlus}` : timeStr;
  }
  function getFirstSegment2(flight) {
    return flight?.segments?.length ? flight.segments[0] : null;
  }
  function getLastSegment2(flight) {
    return flight?.segments?.length ? flight.segments[flight.segments.length - 1] : null;
  }
  function stopsLabel2(flight) {
    const n = flight?.segments?.length || 0;
    return n === 0 ? null : n - 1 === 0 ? "Non-stop" : `${n - 1} stop`;
  }
  function carriersLabel2(flight) {
    const segs = flight?.segments || [];
    const carriers = [];
    for (const s of segs) {
      const c = s?.carrier;
      if (c && !carriers.includes(c)) carriers.push(c);
    }
    return carriers.length ? carriers.join(", ") : null;
  }
  function PlanChoiceCardFlights({ choice, onSelect, disableSelect, cardStyle }) {
    const [showDetails, setShowDetails] = (0, import_react7.useState)(false);
    const { id, label, tags, recommended, flight, flight_details, currency, total_price, total_price_text, price, price_breakdown, title } = choice || {};
    const displayCurrency = price_breakdown?.currency || currency || flight?.currency || "THB";
    const resolvedTotal = typeof total_price === "number" ? total_price : typeof price === "number" ? price : typeof flight?.price_total === "number" ? flight.price_total : null;
    const hasRealPrice = resolvedTotal != null && Number(resolvedTotal) > 0;
    const displayTotalPrice = hasRealPrice ? `${displayCurrency} ${Number(resolvedTotal).toLocaleString("th-TH")}` : total_price_text || "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E49\u0E2D\u0E07\u0E2A\u0E2D\u0E1A\u0E16\u0E32\u0E21";
    const flightDirection = choice?.flight_direction ?? (flight?.segments?.[0]?.direction && String(flight.segments[0].direction).includes("\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A") ? "inbound" : flight?.segments?.[0]?.direction && String(flight.segments[0].direction).includes("\u0E02\u0E32\u0E44\u0E1B") ? "outbound" : null);
    const segmentsForDisplay = (() => {
      let segs = flight?.segments || [];
      if (!segs.length) return segs;
      if (flightDirection === "outbound") segs = segs.filter((s) => s?.direction && String(s.direction).includes("\u0E02\u0E32\u0E44\u0E1B"));
      else if (flightDirection === "inbound") segs = segs.filter((s) => s?.direction && String(s.direction).includes("\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A"));
      return dedupeSegments(segs);
    })();
    const displayFlight = segmentsForDisplay.length ? { ...flight, segments: segmentsForDisplay } : flight;
    const firstSeg = getFirstSegment2(displayFlight);
    const lastSeg = getLastSegment2(displayFlight);
    const flightRoute = firstSeg && lastSeg ? `${firstSeg.from} \u2192 ${lastSeg.to}` : null;
    const isOutbound = flightDirection === "outbound";
    const isInbound = flightDirection === "inbound";
    const flightStops = stopsLabel2(displayFlight);
    const flightCarriers = carriersLabel2(displayFlight);
    const flightPrice = formatMoney(typeof flight?.price_total === "number" ? flight.price_total : null, flight?.currency || displayCurrency);
    let totalJourneyTime = null;
    if (firstSeg && lastSeg && segmentsForDisplay.length > 0) {
      try {
        const firstDepart = firstSeg.depart_at || firstSeg.depart_time;
        let lastArrive = lastSeg.arrive_at || lastSeg.arrive_time;
        if (lastArrive && lastSeg.arrive_plus) {
          const d = new Date(lastArrive);
          const m = String(lastSeg.arrive_plus).match(/\+(\d+)/);
          if (m) d.setDate(d.getDate() + parseInt(m[1], 10));
          lastArrive = d.toISOString();
        }
        if (firstDepart && lastArrive) {
          const diffMs = new Date(lastArrive).getTime() - new Date(firstDepart).getTime();
          if (diffMs > 0) {
            const h = Math.floor(diffMs / (1e3 * 60 * 60));
            const m = Math.floor(diffMs % (1e3 * 60 * 60) / (1e3 * 60));
            totalJourneyTime = h > 0 ? `${h}\u0E0A\u0E21 ${m}\u0E19\u0E32\u0E17\u0E35` : `${m}\u0E19\u0E32\u0E17\u0E35`;
          }
        }
      } catch (e) {
      }
    }
    if (!flight || !flight.segments || flight.segments.length === 0 || segmentsForDisplay.length === 0) {
      return /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card" }, /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react7.default.createElement("span", { className: "plan-card-label" }, "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19 ", title || id)), /* @__PURE__ */ import_react7.default.createElement("p", { className: "plan-card-desc" }, "\u0E44\u0E21\u0E48\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19"), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-footer" }, /* @__PURE__ */ import_react7.default.createElement("button", { className: "plan-card-button", disabled: disableSelect, onClick: () => onSelect && onSelect(id) }, disableSelect ? "\u0E01\u0E23\u0E38\u0E13\u0E32\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E02\u0E32\u0E44\u0E1B\u0E01\u0E48\u0E2D\u0E19" : `\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${id}`)));
    }
    return /* @__PURE__ */ import_react7.default.createElement("div", { className: `plan-card ${recommended ? "plan-card-recommended" : ""}`, style: cardStyle }, /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-title" }, /* @__PURE__ */ import_react7.default.createElement("span", { className: "plan-card-label" }, title || `\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19 ${id}${label ? ` \u2014 ${label}` : ""}`), recommended && (!tags || !tags.includes("\u0E41\u0E19\u0E30\u0E19\u0E33")) && /* @__PURE__ */ import_react7.default.createElement("span", { className: "plan-card-tag" }, "\u0E41\u0E19\u0E30\u0E19\u0E33"), isOutbound && /* @__PURE__ */ import_react7.default.createElement("span", { className: "plan-card-tag", style: { background: "rgba(33, 150, 243, 0.25)", color: "#1976d2", marginLeft: 6, fontSize: 13, padding: "3px 10px" } }, "\u{1F6EB} \u0E02\u0E32\u0E44\u0E1B"), isInbound && /* @__PURE__ */ import_react7.default.createElement("span", { className: "plan-card-tag", style: { background: "rgba(156, 39, 176, 0.25)", color: "#7b1fa2", marginLeft: 6, fontSize: 13, padding: "3px 10px" } }, "\u{1F6EC} \u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A"), (choice?.is_non_stop || flightStops === "Non-stop") && (!tags || !tags.includes("\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07")) && /* @__PURE__ */ import_react7.default.createElement("span", { className: "plan-card-tag", style: { background: "rgba(227, 242, 253, 0.3)", color: "#1976d2", marginLeft: 6, fontSize: 13, padding: "3px 10px" } }, "\u2708\uFE0F \u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07")), tags && Array.isArray(tags) && tags.length > 0 && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-tags" }, [...new Set(tags)].filter((t) => !["Amadeus", "\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07", "\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E17\u0E31\u0E19\u0E17\u0E35", "Google", "\u0E44\u0E21\u0E48\u0E43\u0E0A\u0E48\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07"].includes(t)).filter((t) => t !== "\u0E41\u0E19\u0E30\u0E19\u0E33" || !recommended).filter((t) => t !== "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07" || flightStops !== "Non-stop").map((tag, idx) => /* @__PURE__ */ import_react7.default.createElement("span", { key: idx, className: "plan-tag-pill" }, tag)))), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-section-title" }, "\u2708\uFE0F \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19"), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-section-body" }, firstSeg && lastSeg && /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginBottom: 16, padding: 12, background: "rgba(255,255,255,0.08)", borderRadius: 8, border: "1px solid rgba(255,255,255,0.15)" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: 12 } }, /* @__PURE__ */ import_react7.default.createElement(AirlineLogo2, { carrierCode: firstSeg.carrier, size: 40 }), /* @__PURE__ */ import_react7.default.createElement("div", null, /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontSize: 14, fontWeight: 600 } }, getAirlineName2(firstSeg.carrier)), /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontSize: 12, opacity: 0.7 } }, firstSeg.carrier, firstSeg.flight_number || ""))), /* @__PURE__ */ import_react7.default.createElement("div", { style: { flex: 1, minWidth: 200 } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, marginBottom: 4 } }, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontSize: 16, fontWeight: 600 } }, firstSeg.depart_time || "N/A"), /* @__PURE__ */ import_react7.default.createElement("span", { style: { opacity: 0.6 } }, "\u2013"), /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontSize: 16, fontWeight: 600 } }, getArrivalTimeDisplay2(lastSeg.arrive_at, lastSeg.arrive_plus) || lastSeg.arrive_time || "N/A")), /* @__PURE__ */ import_react7.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", fontSize: 13, opacity: 0.8 } }, totalJourneyTime && /* @__PURE__ */ import_react7.default.createElement("span", null, "\u23F1\uFE0F ", totalJourneyTime), flightRoute && /* @__PURE__ */ import_react7.default.createElement(import_react7.default.Fragment, null, /* @__PURE__ */ import_react7.default.createElement("span", null, "\u2022"), /* @__PURE__ */ import_react7.default.createElement("span", null, "\u{1F4CD} ", flightRoute)), flightStops && /* @__PURE__ */ import_react7.default.createElement("span", { style: { padding: "2px 6px", borderRadius: 4, fontSize: 12, fontWeight: 500, background: flightStops === "Non-stop" ? "rgba(74,222,128,0.2)" : "rgba(255,193,7,0.2)", color: flightStops === "Non-stop" ? "#4ade80" : "#ffc107" } }, getFlightType2(displayFlight.segments) === "\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07" ? "\u2708\uFE0F \u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07" : "\u{1F500} \u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07")), displayFlight.segments.length > 1 && /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginTop: 6, fontSize: 12, opacity: 0.7 } }, displayFlight.segments.slice(0, -1).map((seg, idx) => {
      const layover = calculateLayoverTime2(seg, displayFlight.segments[idx + 1]);
      return layover ? /* @__PURE__ */ import_react7.default.createElement("span", { key: idx, style: { marginRight: 8 } }, seg.to ? `\u0E23\u0E2D\u0E17\u0E35\u0E48 ${getAirportDisplay(seg.to)}` : "\u0E23\u0E2D\u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07", " (", layover, ")") : null;
    }))), /* @__PURE__ */ import_react7.default.createElement("div", { style: { textAlign: "right", minWidth: 100 } }, flightPrice && /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontSize: 18, fontWeight: 700 } }, flightPrice)))), /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginTop: 16, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.25)" } }, (flightStops || flightCarriers) && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { marginBottom: 8 } }, flightStops, flightCarriers ? ` \u2022 ${flightCarriers}` : ""), totalJourneyTime && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { fontWeight: 600 } }, "\u0E40\u0E27\u0E25\u0E32\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14: ", totalJourneyTime), (getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin)) && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { marginTop: 6, fontWeight: 600 } }, "\u0E0A\u0E31\u0E49\u0E19\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23: ", getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin))), flight?.segments?.length > 0 && /* @__PURE__ */ import_react7.default.createElement("button", { type: "button", onClick: () => setShowDetails(!showDetails), style: { marginTop: 8, padding: "6px 12px", background: "rgba(255,255,255,0.15)", border: "1px solid rgba(255,255,255,0.3)", borderRadius: 6, color: "#fff", fontSize: 14, cursor: "pointer" } }, showDetails ? "\u25BC \u0E0B\u0E48\u0E2D\u0E19\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14" : "\u25B6 \u0E14\u0E39\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E40\u0E15\u0E34\u0E21"), /* @__PURE__ */ import_react7.default.createElement("div", { className: `plan-card-details-expandable ${showDetails ? "is-expanded" : ""}` }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { padding: 14, background: "rgba(0,0,0,0.2)", borderRadius: 8, border: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-section-title", style: { marginBottom: 10 } }, "\u{1F4CB} \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14"), displayFlight.segments.map((seg, idx) => {
      const nextSeg = displayFlight.segments[idx + 1];
      const layoverTime = calculateLayoverTime2(seg, nextSeg);
      return /* @__PURE__ */ import_react7.default.createElement("div", { key: idx, style: { marginBottom: idx < displayFlight.segments.length - 1 ? 16 : 12, paddingBottom: idx < displayFlight.segments.length - 1 ? 16 : 0, borderBottom: idx < displayFlight.segments.length - 1 ? "1px solid rgba(255,255,255,0.15)" : "none" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontWeight: 600, marginBottom: 8, fontSize: 16, display: "flex", alignItems: "center", gap: 8 } }, /* @__PURE__ */ import_react7.default.createElement("span", null, seg.direction === "\u0E02\u0E32\u0E44\u0E1B" ? "\u{1F6EB}" : seg.direction === "\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A" ? "\u{1F6EC}" : "\u2708\uFE0F"), /* @__PURE__ */ import_react7.default.createElement("span", null, seg.direction || (idx === 0 ? "\u0E02\u0E32\u0E44\u0E1B" : idx === 1 && displayFlight.segments.length === 2 ? "\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A" : `\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27 ${idx + 1}`))), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { display: "flex", alignItems: "center", gap: 8, marginBottom: 4 } }, /* @__PURE__ */ import_react7.default.createElement(AirlineLogo2, { carrierCode: seg.carrier, size: 28 }), /* @__PURE__ */ import_react7.default.createElement("span", null, "\u0E2A\u0E32\u0E22\u0E01\u0E32\u0E23\u0E1A\u0E34\u0E19: ", getAirlineName2(seg.carrier), " ", seg.carrier && seg.flight_number ? ` \u2022 ${seg.carrier}${seg.flight_number}` : "")), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07: ", seg.from || "-", " \u2192 ", seg.to || "-"), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small" }, "\u0E2D\u0E2D\u0E01: ", seg.depart_time || "-", " \u2192 \u0E16\u0E36\u0E07: ", getArrivalTimeDisplay2(seg.arrive_at, seg.arrive_plus) || seg.arrive_time || "-"), seg.aircraft_code && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07: ", getAircraftName2(seg.aircraft_code)), seg.duration && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small" }, "\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32: ", formatDuration2(seg.duration)), layoverTime && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { marginTop: 6, color: "rgba(255,215,0,0.95)", padding: "4px 8px", background: "rgba(255,215,0,0.2)", borderRadius: 4 } }, "\u23F1\uFE0F \u0E23\u0E2D\u0E04\u0E2D\u0E22\u0E15\u0E48\u0E2D\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07: ", layoverTime, seg.to ? ` \u0E17\u0E35\u0E48 ${getAirportDisplay(seg.to)}` : ""));
    }), /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginTop: 12, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.2)" } }, (flightStops || flightCarriers) && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { marginBottom: 4 } }, flightStops, flightCarriers ? ` \u2022 ${flightCarriers}` : ""), totalJourneyTime && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { fontWeight: 600, marginBottom: 4 } }, "\u0E40\u0E27\u0E25\u0E32\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14: ", totalJourneyTime), (getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin)) && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { fontWeight: 600 } }, "\u0E0A\u0E31\u0E49\u0E19\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23: ", getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin))), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-small", style: { display: "flex", flexDirection: "column", gap: 12, marginTop: 12 } }, flight_details?.price_per_person != null && /* @__PURE__ */ import_react7.default.createElement("div", null, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontWeight: 600 } }, "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E48\u0E2D\u0E04\u0E19:"), " ", Number(flight_details.price_per_person).toLocaleString("th-TH"), " ", flight?.currency || displayCurrency), (flight?.cabin || flight_details?.cabin) && /* @__PURE__ */ import_react7.default.createElement("div", null, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontWeight: 600 } }, "\u0E0A\u0E31\u0E49\u0E19\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23:"), " ", flight?.cabin || flight_details?.cabin), /* @__PURE__ */ import_react7.default.createElement("div", { style: { paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontWeight: 600, marginBottom: 6 } }, "\u{1F9F3} Baggage Allowance"), /* @__PURE__ */ import_react7.default.createElement("div", null, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontWeight: 600 } }, "\u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32\u0E42\u0E2B\u0E25\u0E14 (Checked):"), " ", flight?.baggage || flight_details?.checked_baggage || "\u0E44\u0E21\u0E48\u0E23\u0E27\u0E21"), /* @__PURE__ */ import_react7.default.createElement("div", null, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontWeight: 600 } }, "\u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32\u0E16\u0E37\u0E2D\u0E02\u0E36\u0E49\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07 (Carry-on):"), " ", flight_details?.hand_baggage ?? "1 \u0E01\u0E23\u0E30\u0E40\u0E1B\u0E4B\u0E32\u0E16\u0E37\u0E2D (7 kg)")), /* @__PURE__ */ import_react7.default.createElement("div", { style: { paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontWeight: 600, marginBottom: 6 } }, "\u{1F4CB} Fare Rules"), flight_details?.refundable != null && /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginBottom: 4, padding: "4px 8px", borderRadius: 6, display: "inline-block", width: "fit-content", backgroundColor: flight_details.refundable ? "rgba(74,222,128,0.2)" : "rgba(248,113,113,0.2)", color: flight_details.refundable ? "#4ade80" : "#f87171" } }, "Refundable: ", flight_details.refundable ? "\u2705 \u0E04\u0E37\u0E19\u0E40\u0E07\u0E34\u0E19\u0E44\u0E14\u0E49" : "\u274C \u0E04\u0E37\u0E19\u0E40\u0E07\u0E34\u0E19\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49"), (flight_details?.changeable != null || flight_details?.change_fee) && /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginTop: 4 } }, /* @__PURE__ */ import_react7.default.createElement("span", { style: { padding: "4px 8px", borderRadius: 6, display: "inline-block", backgroundColor: flight_details?.changeable ? "rgba(96,165,250,0.2)" : "rgba(248,113,113,0.2)", color: flight_details?.changeable ? "#60a5fa" : "#f87171" } }, "Changeable: ", flight_details?.changeable ? "\u2705 \u0E40\u0E25\u0E37\u0E48\u0E2D\u0E19\u0E27\u0E31\u0E19\u0E44\u0E14\u0E49" : "\u274C \u0E40\u0E25\u0E37\u0E48\u0E2D\u0E19\u0E27\u0E31\u0E19\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49"), flight_details?.changeable && flight_details?.change_fee && /* @__PURE__ */ import_react7.default.createElement("span", { style: { marginLeft: 8, opacity: 0.9 } }, "\u2022 \u0E04\u0E48\u0E32\u0E18\u0E23\u0E23\u0E21\u0E40\u0E19\u0E35\u0E22\u0E21: ", flight_details.change_fee))), /* @__PURE__ */ import_react7.default.createElement("div", { style: { paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontWeight: 600, marginBottom: 6 } }, "\u2728 \u0E2A\u0E34\u0E48\u0E07\u0E2D\u0E33\u0E19\u0E27\u0E22\u0E04\u0E27\u0E32\u0E21\u0E2A\u0E30\u0E14\u0E27\u0E01 (Amenities)"), /* @__PURE__ */ import_react7.default.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: "8px 16px" } }, /* @__PURE__ */ import_react7.default.createElement("span", null, "\u{1F4F6} WiFi: ", flight_details?.wifi ?? "\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E1A\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07"), /* @__PURE__ */ import_react7.default.createElement("span", null, "\u{1F50C} \u0E1B\u0E25\u0E31\u0E4A\u0E01\u0E44\u0E1F: ", flight_details?.power_outlet ?? "\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E1A\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07"), /* @__PURE__ */ import_react7.default.createElement("span", null, "\u{1F37D}\uFE0F \u0E2D\u0E32\u0E2B\u0E32\u0E23: ", flight_details?.meals ?? "\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E27\u0E48\u0E32\u0E07/\u0E0B\u0E37\u0E49\u0E2D\u0E40\u0E1E\u0E34\u0E48\u0E21"), (flight_details?.seat_width || flight_details?.seat_selection) && /* @__PURE__ */ import_react7.default.createElement("span", null, "\u{1F4BA} \u0E04\u0E27\u0E32\u0E21\u0E01\u0E27\u0E49\u0E32\u0E07\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07: ", flight_details?.seat_width || flight_details?.seat_selection))), (() => {
      const totalHours = flight?.segments?.reduce((s, seg) => s + parseDurationToHours(seg.duration), 0) || 0;
      const estDistKm = totalHours > 0 ? totalHours * 800 : firstSeg?.from && lastSeg?.to ? 1500 : 0;
      const co2Kg = flight_details?.co2_emissions_kg ?? (estDistKm > 0 ? calculateCO2e2(estDistKm) : null);
      return co2Kg != null && co2Kg > 0 ? /* @__PURE__ */ import_react7.default.createElement("div", { style: { paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontWeight: 600, marginBottom: 4 } }, "\u{1F331} CO2 Emissions"), /* @__PURE__ */ import_react7.default.createElement("div", null, "~", co2Kg, " kg CO2e (\u0E1B\u0E23\u0E30\u0E21\u0E32\u0E13\u0E01\u0E32\u0E23)")) : null;
    })(), flight_details?.on_time_performance != null && flight_details.on_time_performance !== "" && /* @__PURE__ */ import_react7.default.createElement("div", { style: { paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.2)" } }, /* @__PURE__ */ import_react7.default.createElement("div", { style: { fontWeight: 600, marginBottom: 4 } }, "\u23F1\uFE0F On-time Performance"), /* @__PURE__ */ import_react7.default.createElement("div", null, flight_details.on_time_performance)), flight_details?.seat_selection && !flight_details?.seat_width && /* @__PURE__ */ import_react7.default.createElement("div", null, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F4BA} \u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07:"), " ", flight_details.seat_selection), flight?.visa_warning && /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginTop: 6, padding: 8, background: "rgba(255,193,7,0.15)", borderRadius: 6, border: "1px solid rgba(255,193,7,0.4)", color: "#facc15", whiteSpace: "pre-line" } }, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F6C2} \u0E2B\u0E21\u0E32\u0E22\u0E40\u0E2B\u0E15\u0E38:"), /* @__PURE__ */ import_react7.default.createElement("br", null), flight.visa_warning), flight_details?.promotions && Array.isArray(flight_details.promotions) && flight_details.promotions.length > 0 && /* @__PURE__ */ import_react7.default.createElement("div", { style: { marginTop: 4 } }, /* @__PURE__ */ import_react7.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F381} \u0E42\u0E1B\u0E23\u0E42\u0E21\u0E0A\u0E31\u0E19:"), /* @__PURE__ */ import_react7.default.createElement("ul", { style: { margin: "4px 0 0 16px", padding: 0 } }, flight_details.promotions.map((promo, idx) => /* @__PURE__ */ import_react7.default.createElement("li", { key: idx }, typeof promo === "string" ? promo : promo?.text || promo?.name || JSON.stringify(promo)))))))))), /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-footer" }, displayTotalPrice && /* @__PURE__ */ import_react7.default.createElement("div", { className: "plan-card-price" }, displayTotalPrice), /* @__PURE__ */ import_react7.default.createElement(
      "button",
      {
        className: "plan-card-button",
        disabled: disableSelect,
        onClick: () => onSelect && onSelect(id),
        title: disableSelect ? "\u0E01\u0E23\u0E38\u0E13\u0E32\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E02\u0E32\u0E44\u0E1B\u0E01\u0E48\u0E2D\u0E19" : void 0
      },
      disableSelect ? "\u0E01\u0E23\u0E38\u0E13\u0E32\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E02\u0E32\u0E44\u0E1B\u0E01\u0E48\u0E2D\u0E19" : `\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${id}`
    )));
  }

  // src/components/bookings/PlanChoiceCardHotels.jsx
  var import_react8 = __toESM(require_react(), 1);
  function formatDate(isoStr) {
    if (!isoStr || typeof isoStr !== "string") return null;
    try {
      const d = isoStr.split("T")[0].split("-");
      if (d.length >= 3) return `${d[2]}/${d[1]}/${d[0]}`;
      return isoStr;
    } catch (_) {
      return isoStr;
    }
  }
  function calcNights(checkIn, checkOut) {
    if (!checkIn || !checkOut) return null;
    try {
      const a = new Date(checkIn.split("T")[0]);
      const b = new Date(checkOut.split("T")[0]);
      const diff = (b - a) / (1e3 * 60 * 60 * 24);
      return Number.isInteger(diff) && diff > 0 ? diff : null;
    } catch (_) {
      return null;
    }
  }
  function PlanChoiceCardHotels({ choice, onSelect, cardStyle }) {
    const { id, label, tags, recommended, hotel, currency, total_price, total_price_text, price_breakdown, price, price_amount, title } = choice || {};
    const toFinite = (v) => typeof v === "number" ? v : typeof v === "string" && v.trim() ? Number(v) : NaN;
    const pickFirstNonNull = (...vals) => {
      for (const v of vals) {
        const n = toFinite(v);
        if (Number.isFinite(n)) return n;
      }
      return null;
    };
    const displayCurrency = price_breakdown?.currency || currency || hotel?.currency || "THB";
    const resolvedTotal = pickFirstNonNull(
      total_price,
      price_amount,
      price,
      hotel?.price_total,
      hotel?.booking?.pricing?.total_amount
    );
    const displayTotalPrice = resolvedTotal != null ? formatPriceInThb(resolvedTotal, displayCurrency) : total_price_text || null;
    const hotelName = hotel?.hotelName || hotel?.name || choice?.title || choice?.raw?.display_name || "Unknown Hotel";
    const hotelNights = hotel?.nights ?? calcNights(hotel?.booking?.check_in_date, hotel?.booking?.check_out_date);
    const checkInStr = formatDate(hotel?.booking?.check_in_date);
    const checkOutStr = formatDate(hotel?.booking?.check_out_date);
    const pricing = hotel?.booking?.pricing;
    const totalAmount = pickFirstNonNull(pricing?.total_amount, hotel?.price_total, resolvedTotal);
    const pricePerNight = pickFirstNonNull(
      pricing?.price_per_night,
      totalAmount != null && hotelNights != null && hotelNights > 0 ? totalAmount / hotelNights : null
    );
    const taxesAndFeesRaw = toFinite(pricing?.taxes_and_fees);
    const taxesAndFees = Number.isFinite(taxesAndFeesRaw) && taxesAndFeesRaw > 0 ? taxesAndFeesRaw : null;
    const pricingCurrency = pricing?.currency || hotel?.currency || displayCurrency;
    const amenityLabels = [];
    if (hotel?.amenities) {
      const a = hotel.amenities;
      if (a.has_wifi) amenityLabels.push("Wi-Fi");
      if (a.has_pool) amenityLabels.push("\u0E2A\u0E23\u0E30\u0E27\u0E48\u0E32\u0E22\u0E19\u0E49\u0E33");
      if (a.has_fitness) amenityLabels.push("\u0E1F\u0E34\u0E15\u0E40\u0E19\u0E2A");
      if (a.has_parking) amenityLabels.push("\u0E17\u0E35\u0E48\u0E08\u0E2D\u0E14\u0E23\u0E16");
      if (a.has_spa) amenityLabels.push("\u0E2A\u0E1B\u0E32");
      if (a.has_air_conditioning) amenityLabels.push("\u0E41\u0E2D\u0E23\u0E4C");
    }
    const mealPlan = hotel?.booking?.policies?.meal_plan || "";
    const mealPlanUpper = (mealPlan || "").toUpperCase();
    if (mealPlanUpper.includes("BREAKFAST") || mealPlanUpper.includes("BFST") || mealPlanUpper.includes("HALF") || mealPlanUpper.includes("FULL")) amenityLabels.push("\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E40\u0E0A\u0E49\u0E32");
    if (mealPlanUpper.includes("LUNCH") || mealPlanUpper.includes("FULL") && mealPlanUpper.includes("BOARD")) amenityLabels.push("\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E01\u0E25\u0E32\u0E07\u0E27\u0E31\u0E19");
    if (mealPlanUpper.includes("DINNER") || mealPlanUpper.includes("HALF") || mealPlanUpper.includes("FULL")) amenityLabels.push("\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E40\u0E22\u0E47\u0E19");
    if (mealPlan && !["\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E40\u0E0A\u0E49\u0E32", "\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E01\u0E25\u0E32\u0E07\u0E27\u0E31\u0E19", "\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E40\u0E22\u0E47\u0E19"].some((m) => amenityLabels.includes(m)) && mealPlan !== "Room Only") amenityLabels.push(mealPlan);
    const originalList = Array.isArray(hotel?.amenities?.original_list) ? hotel.amenities.original_list : [];
    const hasAnyAmenity = amenityLabels.length > 0 || originalList.length > 0;
    if (!hotel) {
      return /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card" }, /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react8.default.createElement("span", { className: "plan-card-label" }, "\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01 ", title || id)), /* @__PURE__ */ import_react8.default.createElement("p", { className: "plan-card-desc" }, "\u0E44\u0E21\u0E48\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01"), /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-footer" }, /* @__PURE__ */ import_react8.default.createElement("button", { className: "plan-card-button", onClick: () => onSelect && onSelect(id) }, "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ", id)));
    }
    return /* @__PURE__ */ import_react8.default.createElement("div", { className: `plan-card ${recommended ? "plan-card-recommended" : ""}`, style: cardStyle }, /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-title" }, /* @__PURE__ */ import_react8.default.createElement("span", { className: "plan-card-label" }, title || `\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01 ${id}${label ? ` \u2014 ${label}` : ""}`), recommended && (!tags || !tags.includes("\u0E41\u0E19\u0E30\u0E19\u0E33")) && /* @__PURE__ */ import_react8.default.createElement("span", { className: "plan-card-tag" }, "\u0E41\u0E19\u0E30\u0E19\u0E33")), tags && Array.isArray(tags) && tags.length > 0 && /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-tags" }, [...new Set(tags)].filter((tag) => !["Amadeus", "\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07", "\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E17\u0E31\u0E19\u0E17\u0E35", "Google", "\u0E44\u0E21\u0E48\u0E43\u0E0A\u0E48\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07"].includes(tag)).map((tag, idx) => /* @__PURE__ */ import_react8.default.createElement("span", { key: idx, className: "plan-tag-pill" }, tag)))), /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F3E8} \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01"), /* @__PURE__ */ import_react8.default.createElement("div", { style: { marginBottom: 12 } }, /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-small", style: { marginBottom: 6, opacity: 0.9 } }, "\u0E20\u0E32\u0E1E\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01"), hotel.visuals?.image_urls && hotel.visuals.image_urls.length > 0 ? /* @__PURE__ */ import_react8.default.createElement("div", { style: { width: "100%", overflowX: "auto", whiteSpace: "nowrap", borderRadius: 8, scrollbarWidth: "none" } }, hotel.visuals.image_urls.map((url, idx) => /* @__PURE__ */ import_react8.default.createElement("img", { key: idx, src: url, alt: "", loading: "lazy", onError: (e) => {
      e.target.style.display = "none";
    }, style: { width: 140, height: 94, objectFit: "cover", borderRadius: 8, marginRight: 8, display: "inline-block" } }))) : /* @__PURE__ */ import_react8.default.createElement("div", { style: { minHeight: 80, background: "rgba(255,255,255,0.08)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.5)", fontSize: 13 } }, "\u0E44\u0E21\u0E48\u0E21\u0E35\u0E20\u0E32\u0E1E")), /* @__PURE__ */ import_react8.default.createElement("div", { style: { display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, marginBottom: 12 } }, /* @__PURE__ */ import_react8.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } }, /* @__PURE__ */ import_react8.default.createElement("span", { className: "plan-card-small", style: { opacity: 0.9 } }, "\u0E23\u0E30\u0E14\u0E31\u0E1A\u0E14\u0E32\u0E27\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01:"), hotel.star_rating != null ? /* @__PURE__ */ import_react8.default.createElement("span", { style: { color: "#FFD700", fontSize: 15 } }, "\u2B50".repeat(Math.round(hotel.star_rating)), " (", hotel.star_rating, " \u0E14\u0E32\u0E27)") : /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontSize: 13, color: "rgba(255,255,255,0.5)" } }, "\u2014")), /* @__PURE__ */ import_react8.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } }, /* @__PURE__ */ import_react8.default.createElement("span", { className: "plan-card-small", style: { opacity: 0.9 } }, "\u0E40\u0E23\u0E17\u0E23\u0E35\u0E27\u0E34\u0E27\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01:"), hotel.visuals?.review_score != null || hotel.rating != null ? /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontSize: 13, background: "#4CAF50", color: "white", padding: "3px 8px", borderRadius: 4 } }, hotel.visuals?.review_score ?? hotel.rating, " / 5 (", (hotel.visuals?.review_count ?? 0) || 0, " \u0E23\u0E35\u0E27\u0E34\u0E27)") : /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontSize: 13, color: "rgba(255,255,255,0.5)" } }, "\u2014"))), /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-section-body" }, (hotel.location?.address || hotel?.address) && /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-small", style: { marginBottom: 8, opacity: 0.9 } }, "\u{1F4CD} ", hotel.location?.address || hotel.address), (hotel.booking?.room?.room_type || hotel.booking?.room?.description) && /* @__PURE__ */ import_react8.default.createElement("div", { style: { marginBottom: 8, paddingLeft: 8, borderLeft: "3px solid rgba(255,255,255,0.3)" } }, /* @__PURE__ */ import_react8.default.createElement("div", { style: { fontWeight: 600, fontSize: 15 } }, "\u{1F6CF}\uFE0F \u0E23\u0E39\u0E1B\u0E41\u0E1A\u0E1A\u0E2B\u0E49\u0E2D\u0E07: ", hotel.booking.room.room_type || hotel.booking.room.description || "Standard"), hotel.booking?.room?.bed_type && /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-small" }, hotel.booking.room.bed_quantity ? `${hotel.booking.room.bed_quantity} x ${hotel.booking.room.bed_type}` : hotel.booking.room.bed_type), hotel.booking?.policies?.meal_plan && /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-small" }, "\u{1F37D}\uFE0F ", hotel.booking.policies.meal_plan)), (hotelNights != null || checkInStr || checkOutStr) && /* @__PURE__ */ import_react8.default.createElement("div", { style: { marginBottom: 8, fontSize: 14 } }, hotelNights != null && /* @__PURE__ */ import_react8.default.createElement("span", null, "\u{1F4C5} \u0E08\u0E33\u0E19\u0E27\u0E19\u0E04\u0E37\u0E19: ", hotelNights, " \u0E04\u0E37\u0E19"), checkInStr && /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E0A\u0E47\u0E04\u0E2D\u0E34\u0E19: ", checkInStr), checkOutStr && /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-small" }, "\u0E40\u0E0A\u0E47\u0E04\u0E40\u0E2D\u0E32\u0E17\u0E4C: ", checkOutStr)), (hasAnyAmenity || hotel?.amenities) && /* @__PURE__ */ import_react8.default.createElement("div", { style: { marginBottom: 12 } }, /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-small", style: { marginBottom: 4, opacity: 0.9 } }, "\u0E2A\u0E48\u0E27\u0E19\u0E01\u0E25\u0E32\u0E07:"), /* @__PURE__ */ import_react8.default.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", padding: 8, background: "rgba(255,255,255,0.1)", borderRadius: 6, fontSize: 16 } }, amenityLabels.length > 0 && amenityLabels.map((txt, i) => /* @__PURE__ */ import_react8.default.createElement("span", { key: i }, txt === "Wi-Fi" && "\u{1F4F6} ", txt === "\u0E2A\u0E23\u0E30\u0E27\u0E48\u0E32\u0E22\u0E19\u0E49\u0E33" && "\u{1F3CA} ", txt === "\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E40\u0E0A\u0E49\u0E32" && "\u{1F373} ", txt === "\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E01\u0E25\u0E32\u0E07\u0E27\u0E31\u0E19" && "\u2600\uFE0F ", txt === "\u0E2D\u0E32\u0E2B\u0E32\u0E23\u0E40\u0E22\u0E47\u0E19" && "\u{1F319} ", txt === "\u0E1F\u0E34\u0E15\u0E40\u0E19\u0E2A" && "\u{1F3CB}\uFE0F ", txt === "\u0E17\u0E35\u0E48\u0E08\u0E2D\u0E14\u0E23\u0E16" && "\u{1F17F}\uFE0F ", txt === "\u0E2A\u0E1B\u0E32" && "\u{1F486} ", txt === "\u0E41\u0E2D\u0E23\u0E4C" && "\u2744\uFE0F ", txt)), amenityLabels.length === 0 && /* @__PURE__ */ import_react8.default.createElement(import_react8.default.Fragment, null, hotel.amenities?.has_wifi && /* @__PURE__ */ import_react8.default.createElement("span", { title: "Wi-Fi" }, "\u{1F4F6} Wi-Fi"), hotel.amenities?.has_pool && /* @__PURE__ */ import_react8.default.createElement("span", { title: "\u0E2A\u0E23\u0E30\u0E27\u0E48\u0E32\u0E22\u0E19\u0E49\u0E33" }, "\u{1F3CA} \u0E2A\u0E23\u0E30\u0E27\u0E48\u0E32\u0E22\u0E19\u0E49\u0E33"), hotel.amenities?.has_fitness && /* @__PURE__ */ import_react8.default.createElement("span", { title: "\u0E1F\u0E34\u0E15\u0E40\u0E19\u0E2A" }, "\u{1F3CB}\uFE0F \u0E1F\u0E34\u0E15\u0E40\u0E19\u0E2A"), hotel.amenities?.has_parking && /* @__PURE__ */ import_react8.default.createElement("span", { title: "\u0E17\u0E35\u0E48\u0E08\u0E2D\u0E14\u0E23\u0E16" }, "\u{1F17F}\uFE0F \u0E17\u0E35\u0E48\u0E08\u0E2D\u0E14\u0E23\u0E16"), hotel.amenities?.has_spa && /* @__PURE__ */ import_react8.default.createElement("span", { title: "\u0E2A\u0E1B\u0E32" }, "\u{1F486} \u0E2A\u0E1B\u0E32"), hotel.amenities?.has_air_conditioning && /* @__PURE__ */ import_react8.default.createElement("span", { title: "\u0E41\u0E2D\u0E23\u0E4C" }, "\u2744\uFE0F \u0E41\u0E2D\u0E23\u0E4C")), originalList.length > 0 && originalList.slice(0, 12).map((item, i) => /* @__PURE__ */ import_react8.default.createElement("span", { key: `orig-${i}`, style: { fontSize: 14, opacity: 0.95 } }, String(item))))), hotel.booking?.policies && /* @__PURE__ */ import_react8.default.createElement("div", { style: { marginBottom: 12 } }, /* @__PURE__ */ import_react8.default.createElement("span", { style: { display: "inline-block", padding: "2px 6px", borderRadius: 4, fontSize: 11, fontWeight: 600, backgroundColor: hotel.booking.policies.is_refundable ? "rgba(74, 222, 128, 0.2)" : "rgba(248, 113, 113, 0.2)", color: hotel.booking.policies.is_refundable ? "#4ade80" : "#f87171" } }, hotel.booking.policies.is_refundable ? "\u2705 \u0E22\u0E01\u0E40\u0E25\u0E34\u0E01\u0E1F\u0E23\u0E35" : "\u274C \u0E2B\u0E49\u0E32\u0E21\u0E22\u0E01\u0E40\u0E25\u0E34\u0E01")), (pricePerNight != null || taxesAndFees != null || totalAmount != null) && /* @__PURE__ */ import_react8.default.createElement("div", { style: { marginTop: 8, paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.2)" } }, pricePerNight != null && /* @__PURE__ */ import_react8.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 } }, /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontSize: 13, opacity: 0.8 } }, "\u0E23\u0E32\u0E04\u0E32\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01 (\u0E15\u0E48\u0E2D\u0E04\u0E37\u0E19)"), /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontWeight: 600 } }, formatPriceInThb(pricePerNight, pricingCurrency))), taxesAndFees != null && /* @__PURE__ */ import_react8.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 } }, /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontSize: 13, opacity: 0.8 } }, "\u0E23\u0E32\u0E04\u0E32\u0E04\u0E48\u0E32\u0E18\u0E23\u0E23\u0E21\u0E40\u0E19\u0E35\u0E22\u0E21"), /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontSize: 13 } }, formatPriceInThb(taxesAndFees, pricingCurrency))), /* @__PURE__ */ import_react8.default.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6, fontSize: 16 } }, /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontWeight: 600 } }, "\u0E23\u0E32\u0E04\u0E32\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01\u0E08\u0E32\u0E01 Amadeus"), /* @__PURE__ */ import_react8.default.createElement("span", { style: { fontWeight: 700, color: "#81c784" } }, formatPriceInThb(totalAmount, pricingCurrency)))))), /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-footer" }, displayTotalPrice && /* @__PURE__ */ import_react8.default.createElement("div", { className: "plan-card-price" }, displayTotalPrice), /* @__PURE__ */ import_react8.default.createElement("button", { className: "plan-card-button", onClick: () => onSelect && onSelect(id) }, "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ", id)));
  }

  // src/components/bookings/PlanChoiceCardTransfer.jsx
  var import_react9 = __toESM(require_react(), 1);
  function transportTypeLabel(transport, car) {
    if (car) return "\u{1F697} \u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32";
    if (transport?.type === "car_rental") return "\u{1F697} \u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32";
    if (transport?.type === "bus") return "\u{1F68C} \u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23";
    if (transport?.type === "train") return "\u{1F682} \u0E23\u0E16\u0E44\u0E1F";
    if (transport?.type === "metro") return "\u{1F687} \u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32";
    if (transport?.type === "ferry") return "\u26F4\uFE0F \u0E40\u0E23\u0E37\u0E2D";
    if (transport?.type === "transfer") return "\u{1F697} \u0E23\u0E16\u0E23\u0E31\u0E1A\u0E2A\u0E48\u0E07";
    return "\u{1F697} \u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07";
  }
  function transportTypeName(transport) {
    if (!transport?.type) return "";
    const names = { car_rental: "\u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32", bus: "\u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23", train: "\u0E23\u0E16\u0E44\u0E1F", metro: "\u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32", ferry: "\u0E40\u0E23\u0E37\u0E2D", transfer: "\u0E23\u0E16\u0E23\u0E31\u0E1A\u0E2A\u0E48\u0E07" };
    return names[transport.type] || transport.type;
  }
  function PlanChoiceCardTransfer({ choice, onSelect, cardStyle }) {
    const { id, label, tags, recommended, transport, car, ground_transport, currency, total_price, total_price_text, price, price_breakdown, title } = choice || {};
    const displayCurrency = price_breakdown?.currency || currency || transport?.currency || car?.currency || "THB";
    const transportPrice = transport?.price ?? transport?.price_amount ?? transport?.data?.price ?? car?.price ?? car?.price_amount;
    const resolvedTotal = typeof total_price === "number" ? total_price : typeof price === "number" ? price : typeof transportPrice === "number" ? transportPrice : null;
    const hasRealPrice = resolvedTotal != null && Number(resolvedTotal) > 0;
    const displayTotalPrice = hasRealPrice ? formatPriceInThb(resolvedTotal, displayCurrency) : total_price_text || "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E49\u0E2D\u0E07\u0E2A\u0E2D\u0E1A\u0E16\u0E32\u0E21";
    const hasContent = ground_transport || transport || car;
    if (!hasContent) {
      return /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card" }, /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react9.default.createElement("span", { className: "plan-card-label" }, "\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 ", title || id)), /* @__PURE__ */ import_react9.default.createElement("p", { className: "plan-card-desc" }, "\u0E44\u0E21\u0E48\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-footer" }, /* @__PURE__ */ import_react9.default.createElement("button", { className: "plan-card-button", onClick: () => onSelect && onSelect(id) }, "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ", id)));
    }
    return /* @__PURE__ */ import_react9.default.createElement("div", { className: `plan-card ${recommended ? "plan-card-recommended" : ""}`, style: cardStyle }, /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-title" }, /* @__PURE__ */ import_react9.default.createElement("span", { className: "plan-card-label" }, title || `\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 ${id}${label ? ` \u2014 ${label}` : ""}`), recommended && (!tags || !tags.includes("\u0E41\u0E19\u0E30\u0E19\u0E33")) && /* @__PURE__ */ import_react9.default.createElement("span", { className: "plan-card-tag" }, "\u0E41\u0E19\u0E30\u0E19\u0E33")), tags && Array.isArray(tags) && tags.length > 0 && /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-tags" }, [...new Set(tags)].filter((tag) => !["Amadeus", "\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07", "\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E17\u0E31\u0E19\u0E17\u0E35", "Google", "\u0E44\u0E21\u0E48\u0E43\u0E0A\u0E48\u0E23\u0E32\u0E04\u0E32\u0E08\u0E23\u0E34\u0E07"].includes(tag)).map((tag, idx) => /* @__PURE__ */ import_react9.default.createElement("span", { key: idx, className: "plan-tag-pill" }, tag)))), ground_transport && /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F697} \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, typeof ground_transport === "string" ? ground_transport.split("\n").map((line, idx) => /* @__PURE__ */ import_react9.default.createElement("div", { key: idx }, line)) : ground_transport.description && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 12, fontSize: 15, lineHeight: 1.6 } }, ground_transport.description))), (transport || car) && /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-section-title" }, transportTypeLabel(transport, car)), /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, transport?.type && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 8, fontSize: 16, fontWeight: 600 } }, "\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17: ", transportTypeName(transport)), (transport?.route || transport?.data?.route || car?.route) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 8, fontSize: 15 } }, /* @__PURE__ */ import_react9.default.createElement("span", { style: { fontWeight: 600 } }, "\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07: "), transport?.route || transport?.data?.route || car?.route), (transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 12, padding: 12, background: "rgba(74, 222, 128, 0.15)", borderRadius: 8, border: "1px solid rgba(74, 222, 128, 0.3)" } }, /* @__PURE__ */ import_react9.default.createElement("div", { style: { fontSize: 18, fontWeight: 700, color: "#4ade80", marginBottom: 4 } }, "\u{1F4B0} \u0E23\u0E32\u0E04\u0E32: ", formatMoney(transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount, transport?.currency || transport?.data?.currency || car?.currency || "THB")), (transport?.price_per_day || car?.price_per_day) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { fontSize: 14, opacity: 0.9, marginTop: 4 } }, "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E48\u0E2D\u0E27\u0E31\u0E19: ", formatMoney(transport?.price_per_day || car?.price_per_day, transport?.currency || car?.currency || "THB"))), (transport?.duration || transport?.data?.duration || car?.duration) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 8, fontSize: 15 } }, /* @__PURE__ */ import_react9.default.createElement("span", { style: { fontWeight: 600 } }, "\u23F1\uFE0F \u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32: "), formatDuration2(transport?.duration || transport?.data?.duration || car?.duration) || (transport?.duration || transport?.data?.duration || car?.duration)), (transport?.distance || transport?.data?.distance || car?.distance) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 8, fontSize: 15 } }, /* @__PURE__ */ import_react9.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F4CF} \u0E23\u0E30\u0E22\u0E30\u0E17\u0E32\u0E07: "), typeof (transport?.distance || transport?.data?.distance || car?.distance) === "number" ? `${(transport?.distance || transport?.data?.distance || car?.distance).toLocaleString("th-TH")} \u0E01\u0E21.` : transport?.distance || transport?.data?.distance || car?.distance), (transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 8, fontSize: 15 } }, /* @__PURE__ */ import_react9.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F3E2} \u0E1A\u0E23\u0E34\u0E29\u0E31\u0E17: "), transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company), (transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 8, fontSize: 15 } }, /* @__PURE__ */ import_react9.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F699} \u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E23\u0E16: "), transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type), (transport?.seats || car?.seats || transport?.capacity || car?.capacity) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginBottom: 8, fontSize: 15 } }, /* @__PURE__ */ import_react9.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F4BA} \u0E08\u0E33\u0E19\u0E27\u0E19\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07: "), transport?.seats || car?.seats || transport?.capacity || car?.capacity, " \u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07"), (transport?.details || transport?.data?.details || car?.details) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginTop: 12, padding: 10, background: "rgba(255,255,255,0.1)", borderRadius: 6 } }, /* @__PURE__ */ import_react9.default.createElement("div", { style: { fontWeight: 600, marginBottom: 6 } }, "\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E40\u0E1E\u0E34\u0E48\u0E21\u0E40\u0E15\u0E34\u0E21:"), Array.isArray(transport?.details || transport?.data?.details || car?.details) ? (transport?.details || transport?.data?.details || car?.details).map((d, i) => /* @__PURE__ */ import_react9.default.createElement("div", { key: i, style: { marginBottom: 4 } }, "\u2022 ", d)) : /* @__PURE__ */ import_react9.default.createElement("div", null, transport?.details || transport?.data?.details || car?.details)), (transport?.features || car?.features || transport?.amenities || car?.amenities) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginTop: 12, padding: 10, background: "rgba(255,255,255,0.1)", borderRadius: 6 } }, /* @__PURE__ */ import_react9.default.createElement("div", { style: { fontWeight: 600, marginBottom: 6 } }, "\u0E04\u0E38\u0E13\u0E2A\u0E21\u0E1A\u0E31\u0E15\u0E34:"), Array.isArray(transport?.features || car?.features || transport?.amenities || car?.amenities) ? (transport?.features || car?.features || transport?.amenities || car?.amenities).map((f, i) => /* @__PURE__ */ import_react9.default.createElement("div", { key: i, style: { marginBottom: 4 } }, "\u2713 ", f)) : /* @__PURE__ */ import_react9.default.createElement("div", null, transport?.features || car?.features || transport?.amenities || car?.amenities)), (transport?.note || transport?.data?.note || car?.note) && /* @__PURE__ */ import_react9.default.createElement("div", { style: { marginTop: 12, padding: 10, background: "rgba(255, 193, 7, 0.15)", borderRadius: 6, fontSize: 14 } }, /* @__PURE__ */ import_react9.default.createElement("span", { style: { fontWeight: 600 } }, "\u{1F4DD} \u0E2B\u0E21\u0E32\u0E22\u0E40\u0E2B\u0E15\u0E38: "), transport?.note || transport?.data?.note || car?.note))), /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-footer" }, displayTotalPrice && /* @__PURE__ */ import_react9.default.createElement("div", { className: "plan-card-price" }, displayTotalPrice), /* @__PURE__ */ import_react9.default.createElement("button", { className: "plan-card-button", onClick: () => onSelect && onSelect(id) }, "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ", id)));
  }

  // src/components/chat/BookingProgressBar.jsx
  var import_react10 = __toESM(require_react(), 1);
  var STEPS = [
    {
      key: "confirming_search",
      label: "\u0E04\u0E49\u0E19\u0E2B\u0E32",
      icon: "\u{1F50D}",
      description: "\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E17\u0E23\u0E34\u0E1B"
    },
    {
      key: "selecting",
      label: "\u0E40\u0E25\u0E37\u0E2D\u0E01",
      icon: "\u2708\uFE0F",
      description: "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19 & \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01"
    },
    {
      key: "confirming_booking",
      label: "\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19",
      icon: "\u{1F4CB}",
      description: "\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07"
    },
    {
      key: "completed",
      label: "\u0E08\u0E2D\u0E07",
      icon: "\u{1F389}",
      description: "\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08"
    }
  ];
  var STATE_TO_STEP_INDEX = {
    idle: -1,
    confirming_search: 0,
    searching: 0,
    selecting: 1,
    confirming_booking: 2,
    completed: 3
  };
  function BookingProgressBar({ funnelState }) {
    const activeIndex = STATE_TO_STEP_INDEX[funnelState] ?? -1;
    if (activeIndex < 0) return null;
    return /* @__PURE__ */ import_react10.default.createElement(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "8px 16px",
          background: "rgba(0, 0, 0, 0.2)",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          gap: "0",
          userSelect: "none"
        }
      },
      STEPS.map((step, idx) => {
        const isDone = idx < activeIndex;
        const isActive = idx === activeIndex;
        const isFuture = idx > activeIndex;
        return /* @__PURE__ */ import_react10.default.createElement(import_react10.default.Fragment, { key: step.key }, /* @__PURE__ */ import_react10.default.createElement(
          "div",
          {
            style: {
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "3px",
              minWidth: "64px"
            }
          },
          /* @__PURE__ */ import_react10.default.createElement(
            "div",
            {
              style: {
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: isDone ? "14px" : "16px",
                background: isDone ? "rgba(34, 197, 94, 0.25)" : isActive ? "rgba(59, 130, 246, 0.35)" : "rgba(255,255,255,0.06)",
                border: isDone ? "1.5px solid rgba(34, 197, 94, 0.6)" : isActive ? "2px solid rgba(99, 179, 246, 0.8)" : "1.5px solid rgba(255,255,255,0.12)",
                boxShadow: isActive ? "0 0 8px rgba(99,179,246,0.4)" : "none",
                transition: "all 0.3s ease"
              }
            },
            isDone ? "\u2713" : step.icon
          ),
          /* @__PURE__ */ import_react10.default.createElement(
            "span",
            {
              style: {
                fontSize: "10px",
                fontWeight: isActive ? "600" : "400",
                color: isDone ? "rgba(134, 239, 172, 0.9)" : isActive ? "rgba(147, 197, 253, 1)" : "rgba(255,255,255,0.3)",
                whiteSpace: "nowrap",
                transition: "color 0.3s ease"
              }
            },
            step.label
          )
        ), idx < STEPS.length - 1 && /* @__PURE__ */ import_react10.default.createElement(
          "div",
          {
            style: {
              flex: 1,
              height: "2px",
              marginBottom: "14px",
              background: idx < activeIndex ? "rgba(34, 197, 94, 0.5)" : "rgba(255,255,255,0.08)",
              transition: "background 0.4s ease",
              minWidth: "16px"
            }
          }
        ));
      })
    );
  }

  // src/components/bookings/TripSummaryUI.jsx
  var import_react11 = __toESM(require_react(), 1);
  function moneyThb(amount, sourceCurrency) {
    return formatPriceInThb(amount, sourceCurrency);
  }
  function safeText(v) {
    if (v == null) return "";
    return String(v);
  }
  function kv(label, value) {
    const v = safeText(value).trim();
    return /* @__PURE__ */ import_react11.default.createElement("div", { className: "summary-kv" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "summary-k" }, label), /* @__PURE__ */ import_react11.default.createElement("div", { className: "summary-v" }, v || "\u2014"));
  }
  function formatDateThai(dateStr) {
    if (!dateStr || typeof dateStr !== "string") return "";
    const d = /* @__PURE__ */ new Date(dateStr.trim() + "T00:00:00");
    if (Number.isNaN(d.getTime())) return dateStr;
    const day = d.getDate();
    const months = ["\u0E21\u0E01\u0E23\u0E32\u0E04\u0E21", "\u0E01\u0E38\u0E21\u0E20\u0E32\u0E1E\u0E31\u0E19\u0E18\u0E4C", "\u0E21\u0E35\u0E19\u0E32\u0E04\u0E21", "\u0E40\u0E21\u0E29\u0E32\u0E22\u0E19", "\u0E1E\u0E24\u0E29\u0E20\u0E32\u0E04\u0E21", "\u0E21\u0E34\u0E16\u0E38\u0E19\u0E32\u0E22\u0E19", "\u0E01\u0E23\u0E01\u0E0E\u0E32\u0E04\u0E21", "\u0E2A\u0E34\u0E07\u0E2B\u0E32\u0E04\u0E21", "\u0E01\u0E31\u0E19\u0E22\u0E32\u0E22\u0E19", "\u0E15\u0E38\u0E25\u0E32\u0E04\u0E21", "\u0E1E\u0E24\u0E28\u0E08\u0E34\u0E01\u0E32\u0E22\u0E19", "\u0E18\u0E31\u0E19\u0E27\u0E32\u0E04\u0E21"];
    const month = months[d.getMonth()];
    const be = d.getFullYear() + 543;
    return `${day} ${month} ${be}`;
  }
  function getAirlineName3(code) {
    if (!code) return "Unknown";
    return AIRLINE_NAMES[String(code).toUpperCase()] || code;
  }
  function getAirlineLogoUrl(carrierCode, attempt = 1) {
    if (!carrierCode) return null;
    const code = carrierCode.toUpperCase();
    switch (attempt) {
      case 1:
        return `https://logos.skyscnr.com/images/airlines/favicon/${code}.png`;
      case 2:
        return `https://avicon.io/api/airlines/${code}`;
      case 3:
        return `https://www.airlinecodes.info/airline-logos/${code}.png`;
      case 4:
        return `https://d1yjjnpx0p53s8.cloudfront.net/images/airlines/${code}.png`;
      case 5: {
        const domain = AIRLINE_DOMAINS[code];
        if (domain) {
          return `https://www.google.com/s2/favicons?sz=128&domain=${domain}`;
        }
        return null;
      }
      case 6:
        return `https://pics.avs.io/200/200/${code}.png`;
      default:
        return null;
    }
  }
  function AirlineLogo3({ carrierCode, size = 32, style = {} }) {
    const [logoAttempt, setLogoAttempt] = import_react11.default.useState(1);
    const [logoError, setLogoError] = import_react11.default.useState(false);
    const [currentUrl, setCurrentUrl] = import_react11.default.useState(null);
    import_react11.default.useEffect(() => {
      if (carrierCode) {
        setLogoAttempt(1);
        setLogoError(false);
        setCurrentUrl(getAirlineLogoUrl(carrierCode, 1));
      }
    }, [carrierCode]);
    const handleImageError = () => {
      const maxAttempts = 6;
      let nextAttempt = logoAttempt + 1;
      let url = getAirlineLogoUrl(carrierCode, nextAttempt);
      while (!url && nextAttempt < maxAttempts) {
        nextAttempt += 1;
        url = getAirlineLogoUrl(carrierCode, nextAttempt);
      }
      if (url) {
        setLogoAttempt(nextAttempt);
        setCurrentUrl(url);
      } else {
        setLogoError(true);
      }
    };
    if (!carrierCode || logoError || !currentUrl) {
      return /* @__PURE__ */ import_react11.default.createElement("div", { style: {
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: "6px",
        background: "rgba(255, 255, 255, 0.1)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: `${Math.max(10, size * 0.35)}px`,
        fontWeight: "600",
        color: "#fff",
        ...style
      } }, carrierCode || "N/A");
    }
    return /* @__PURE__ */ import_react11.default.createElement(
      "img",
      {
        src: currentUrl,
        alt: `${carrierCode} logo`,
        style: {
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: "6px",
          objectFit: "contain",
          background: "rgba(255, 255, 255, 0.05)",
          padding: "4px",
          ...style
        },
        onError: handleImageError,
        onLoad: () => {
          if (logoError) setLogoError(false);
        }
      }
    );
  }
  function formatDuration3(isoDuration) {
    if (!isoDuration) return "";
    const match = isoDuration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
    if (!match) return isoDuration;
    const hours = parseInt(match[1] || 0);
    const minutes = parseInt(match[2] || 0);
    const parts = [];
    if (hours > 0) parts.push(`${hours} \u0E0A\u0E31\u0E48\u0E27\u0E42\u0E21\u0E07`);
    if (minutes > 0) parts.push(`${minutes} \u0E19\u0E32\u0E17\u0E35`);
    return parts.join(" ") || "0 \u0E19\u0E32\u0E17\u0E35";
  }
  function formatThaiDate(isoDate) {
    if (!isoDate) return "";
    try {
      let dateStr = isoDate;
      if (dateStr.includes("T")) {
        dateStr = dateStr.split("T")[0];
      }
      const date = /* @__PURE__ */ new Date(dateStr + "T00:00:00");
      if (isNaN(date.getTime())) return isoDate;
      const day = date.getDate();
      const month = date.getMonth() + 1;
      const year = date.getFullYear() + 543;
      return `${day}/${month}/${year}`;
    } catch (e) {
      console.error("Error formatting Thai date:", e);
      return isoDate;
    }
  }
  function formatThaiDateTime(isoDateTime) {
    if (!isoDateTime) return "";
    try {
      const date = new Date(isoDateTime);
      if (isNaN(date.getTime())) return isoDateTime;
      const day = date.getDate();
      const month = date.getMonth() + 1;
      const year = date.getFullYear() + 543;
      const hours = String(date.getHours()).padStart(2, "0");
      const minutes = String(date.getMinutes()).padStart(2, "0");
      return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch (e) {
      console.error("Error formatting Thai datetime:", e);
      return isoDateTime;
    }
  }
  function splitFlightSegmentsToOutboundInbound(segments, travelSlots) {
    if (!Array.isArray(segments) || segments.length === 0) return { outbound: [], inbound: [] };
    if (segments.length === 1) return { outbound: segments, inbound: [] };
    const origin = (travelSlots?.origin_city || travelSlots?.origin || segments[0]?.from || "").toString().trim().toUpperCase();
    if (origin) {
      const originArrivalIndex = segments.findIndex((seg, idx) => idx > 0 && (seg.to || "").toString().trim().toUpperCase() === origin);
      if (originArrivalIndex > 0) {
        return {
          outbound: segments.slice(0, originArrivalIndex),
          inbound: segments.slice(originArrivalIndex)
        };
      }
    }
    const mid = Math.ceil(segments.length / 2);
    return { outbound: segments.slice(0, mid), inbound: segments.slice(mid) };
  }
  function TripSummaryCard({ plan, travelSlots, cachedOptions, cacheValidation, workflowValidation }) {
    if (!plan) return null;
    const validationIssues = cacheValidation?.issues || [];
    const validationWarnings = cacheValidation?.warnings || [];
    const currency = plan?.price_breakdown?.currency || plan?.currency || plan?.flight?.currency || plan?.travel?.flights?.currency || plan?.hotel?.currency || plan?.accommodation?.currency || "THB";
    const _flight = travelSlots?.flight ?? plan?.flight ?? plan?.travel?.flights ?? {};
    const _hotel = travelSlots?.hotel ?? plan?.hotel ?? plan?.accommodation ?? {};
    const _transport = travelSlots?.transport ?? plan?.transport ?? plan?.travel?.ground_transport;
    const _transportObj = _transport && !Array.isArray(_transport) ? _transport : Array.isArray(_transport) ? { segments: _transport } : {};
    const rawF = Number(_flight?.total_price ?? _flight?.price_total ?? 0) || 0;
    const rawH = Number(_hotel?.total_price ?? _hotel?.price_total ?? 0) || (Array.isArray(_hotel?.segments) ? _hotel.segments.reduce((a, s) => a + Number(s?.price ?? s?.price_total ?? 0), 0) : 0);
    const rawT = Number(_transportObj?.price ?? _transportObj?.price_amount ?? 0) || (Array.isArray(_transportObj?.segments) ? _transportObj.segments.reduce((a, s) => a + Number(s?.price ?? s?.price_amount ?? 0), 0) : 0);
    const sumFThb = toThb(rawF, _flight?.currency || "THB") ?? 0;
    const sumHThb = toThb(rawH, _hotel?.currency || "THB") ?? 0;
    const sumTThb = Array.isArray(_transportObj?.segments) && _transportObj.segments.length > 0 ? _transportObj.segments.reduce((a, s) => a + (toThb(Number(s?.price ?? s?.price_amount ?? 0), s?.currency || "THB") ?? 0), 0) : toThb(rawT, _transportObj?.currency || "THB") ?? 0;
    const totalFromItemsThb = sumFThb + sumHThb + sumTThb;
    const total = totalFromItemsThb > 0 ? totalFromItemsThb : typeof plan?.total_price === "number" ? toThb(plan.total_price, plan?.currency || "THB") ?? plan.total_price : typeof plan?.price === "number" ? toThb(plan.price, plan?.currency || "THB") ?? plan.price : typeof plan?.summary?.total_price === "number" ? toThb(plan.summary.total_price, plan?.summary?.currency || plan?.currency || "THB") ?? plan.summary.total_price : void 0;
    const totalText = total != null ? moneyThb(total, "THB") : safeText(plan?.total_price_text || plan?.summary?.total_price_text) || "\u2014";
    const legs = Array.isArray(travelSlots?.legs) ? travelSlots.legs : [];
    const isMultiCity = legs.length > 1;
    const origin = travelSlots?.origin_city || travelSlots?.origin || travelSlots?.origin_iata || legs[0]?.origin || "";
    const dest = travelSlots?.destination_city || travelSlots?.destination || travelSlots?.destination_iata || (legs.length ? legs[legs.length - 1]?.destination : "");
    const dateGo = travelSlots?.departure_date || travelSlots?.start_date || travelSlots?.check_in || legs[0]?.departure_date || "";
    let dateBack = travelSlots?.return_date || travelSlots?.end_date || travelSlots?.check_out || "";
    if (!dateBack && dateGo && travelSlots?.nights != null) {
      try {
        const startDate = new Date(dateGo);
        const nights = parseInt(travelSlots.nights) || 0;
        const returnDate = new Date(startDate);
        returnDate.setDate(returnDate.getDate() + nights);
        dateBack = returnDate.toISOString().split("T")[0];
      } catch (e) {
        console.error("Error calculating return date:", e);
      }
    }
    const pax = [
      travelSlots?.adults != null && Number(travelSlots.adults) > 0 ? `${travelSlots.adults} \u0E1C\u0E39\u0E49\u0E43\u0E2B\u0E0D\u0E48` : null,
      travelSlots?.children != null && Number(travelSlots.children) > 0 ? `${travelSlots.children} \u0E40\u0E14\u0E47\u0E01` : null
    ].filter(Boolean).join(", ");
    const flightData = plan?.flight || plan?.travel?.flights || {};
    const flight = flightData;
    const flightSegments = dedupeSegments(flight?.segments || []);
    const firstSegment = flightSegments[0];
    const lastSegment = flightSegments[flightSegments.length - 1];
    const hasOutboundInbound = flight?.outbound?.length > 0 || flight?.inbound?.length > 0;
    const split = hasOutboundInbound ? null : splitFlightSegmentsToOutboundInbound(flightSegments, travelSlots);
    const outboundSegments = dedupeSegments(hasOutboundInbound ? flight.outbound || [] : split?.outbound || []);
    const inboundSegments = dedupeSegments(hasOutboundInbound ? flight.inbound || [] : split?.inbound || []);
    const hotel = plan?.hotel || plan?.accommodation || {};
    const hotelSegments = hotel?.segments || [];
    const transportRaw = plan?.transport || plan?.travel?.ground_transport || {};
    const transport = Array.isArray(transportRaw) ? { segments: transportRaw } : transportRaw;
    const transportSegments = transport?.segments || [];
    const hasFlightData = flightSegments.length > 0 || outboundSegments.length > 0;
    const hasHotelData = hotelSegments.length > 0 || !!hotel.hotelName;
    const hasTransportData = transportSegments.length > 0 || !!transport.type;
    const isRoundTrip = inboundSegments.length > 0 || !!dateBack;
    const routeLabel = isMultiCity ? "\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07 (\u0E2B\u0E25\u0E32\u0E22\u0E2A\u0E16\u0E32\u0E19\u0E17\u0E35\u0E48)" : hasHotelData && !hasFlightData ? "\u0E2A\u0E16\u0E32\u0E19\u0E17\u0E35\u0E48" : "\u0E15\u0E49\u0E19\u0E17\u0E32\u0E07 \u2192 \u0E1B\u0E25\u0E32\u0E22\u0E17\u0E32\u0E07";
    const routeText = isMultiCity && legs.length ? [legs[0]?.origin, ...legs.map((l) => l.destination)].filter(Boolean).join(" \u2192 ") : origin && dest ? `${origin} \u2192 ${dest}` : origin || dest;
    const summaryTitle = (() => {
      if (hasFlightData && hasHotelData) return "\u2705 \u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B (\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19 + \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01)";
      if (hasFlightData && !hasHotelData) return "\u2705 \u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B (\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19)";
      if (!hasFlightData && hasHotelData) return "\u2705 \u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B (\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01)";
      if (hasTransportData) return "\u2705 \u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B (\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07)";
      return "\u2705 \u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B";
    })();
    const outboundList = flight?.outbound || plan?.travel?.flights?.outbound || [];
    const inboundList = flight?.inbound || plan?.travel?.flights?.inbound || [];
    const accommodationList = hotel?.segments || plan?.accommodation?.segments || [];
    const groundList = transport?.segments || plan?.travel?.ground_transport || [];
    const summaryFromPlanCard = {
      flights_outbound: Array.isArray(outboundList) ? outboundList.length : outboundList ? 1 : 0,
      flights_inbound: Array.isArray(inboundList) ? inboundList.length : inboundList ? 1 : 0,
      ground_transport: Array.isArray(groundList) ? groundList.length : groundList ? 1 : 0,
      accommodation: Array.isArray(accommodationList) ? accommodationList.length : accommodationList ? 1 : 0
    };
    const cacheSum = cacheValidation?.summary;
    const cacheHasAny = cacheSum && (cacheSum.flights_outbound || 0) + (cacheSum.flights_inbound || 0) + (cacheSum.ground_transport || 0) + (cacheSum.accommodation || 0) > 0;
    const effectiveSum = cacheHasAny ? cacheSum : summaryFromPlanCard;
    return /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card plan-card-summary" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-title" }, /* @__PURE__ */ import_react11.default.createElement("span", { className: "plan-card-label" }, summaryTitle))), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F9FE} \u0E20\u0E32\u0E1E\u0E23\u0E27\u0E21"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, (origin || dest || routeText) && kv(routeLabel, routeText), dateGo && kv(hasHotelData && !hasFlightData ? "\u0E27\u0E31\u0E19\u0E40\u0E0A\u0E47\u0E04\u0E2D\u0E34\u0E19" : "\u0E27\u0E31\u0E19\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07", formatThaiDate(dateGo)), dateBack && kv(hasHotelData && !hasFlightData ? "\u0E27\u0E31\u0E19\u0E40\u0E0A\u0E47\u0E04\u0E40\u0E2D\u0E32\u0E17\u0E4C" : "\u0E27\u0E31\u0E19\u0E01\u0E25\u0E31\u0E1A", formatThaiDate(dateBack)), pax && kv(hasHotelData && !hasFlightData ? "\u0E08\u0E33\u0E19\u0E27\u0E19\u0E1C\u0E39\u0E49\u0E40\u0E02\u0E49\u0E32\u0E1E\u0E31\u0E01" : "\u0E1C\u0E39\u0E49\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23", pax))), flightSegments.length > 0 && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u2708\uFE0F \u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, outboundSegments.length > 0 && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginBottom: inboundSegments.length > 0 ? "16px" : "0" } }, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontWeight: 600, marginBottom: "8px", color: "#2563eb", display: "flex", alignItems: "center", gap: "8px" } }, "\u{1F6EB} \u0E02\u0E32\u0E44\u0E1B"), outboundSegments.map((seg, idx) => {
      const isLast = idx === outboundSegments.length - 1;
      return /* @__PURE__ */ import_react11.default.createElement("div", { key: idx, style: { marginBottom: isLast ? "0" : "12px", paddingLeft: "8px", borderLeft: "3px solid #3b82f6" } }, seg.carrier && /* @__PURE__ */ import_react11.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px", flexWrap: "wrap" } }, /* @__PURE__ */ import_react11.default.createElement(AirlineLogo3, { carrierCode: seg.carrier, size: 36 }), /* @__PURE__ */ import_react11.default.createElement("div", null, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontWeight: 600, fontSize: "14px" } }, getAirlineName3(seg.carrier)), seg.number && /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontSize: "12px", opacity: 0.85 } }, seg.carrier, seg.number))), seg.from && seg.to && kv("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", `${seg.from} \u2192 ${seg.to}`), seg.departure && kv("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E2D\u0E2D\u0E01", formatThaiDateTime(seg.departure)), seg.arrival && kv("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E16\u0E36\u0E07", formatThaiDateTime(seg.arrival)), seg.duration && kv("\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32", formatDuration3(seg.duration)), !isLast && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px", fontSize: "12px", color: "#6b7280" } }, "\u21AA \u0E41\u0E27\u0E30\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07"));
    })), inboundSegments.length > 0 && /* @__PURE__ */ import_react11.default.createElement("div", null, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontWeight: 600, marginBottom: "8px", color: "#2563eb", display: "flex", alignItems: "center", gap: "8px" } }, "\u{1F6EC} \u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A"), inboundSegments.map((seg, idx) => {
      const isLast = idx === inboundSegments.length - 1;
      return /* @__PURE__ */ import_react11.default.createElement("div", { key: idx, style: { marginBottom: isLast ? "0" : "12px", paddingLeft: "8px", borderLeft: "3px solid #10b981" } }, seg.carrier && /* @__PURE__ */ import_react11.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px", flexWrap: "wrap" } }, /* @__PURE__ */ import_react11.default.createElement(AirlineLogo3, { carrierCode: seg.carrier, size: 36 }), /* @__PURE__ */ import_react11.default.createElement("div", null, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontWeight: 600, fontSize: "14px" } }, getAirlineName3(seg.carrier)), seg.number && /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontSize: "12px", opacity: 0.85 } }, seg.carrier, seg.number))), seg.from && seg.to && kv("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", `${seg.from} \u2192 ${seg.to}`), seg.departure && kv("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E2D\u0E2D\u0E01", formatThaiDateTime(seg.departure)), seg.arrival && kv("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E16\u0E36\u0E07", formatThaiDateTime(seg.arrival)), seg.duration && kv("\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32", formatDuration3(seg.duration)), !isLast && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px", fontSize: "12px", color: "#6b7280" } }, "\u21AA \u0E41\u0E27\u0E30\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E40\u0E04\u0E23\u0E37\u0E48\u0E2D\u0E07"));
    })), outboundSegments.length === 0 && inboundSegments.length === 0 && firstSegment && /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, firstSegment.carrier && /* @__PURE__ */ import_react11.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px", flexWrap: "wrap" } }, /* @__PURE__ */ import_react11.default.createElement(AirlineLogo3, { carrierCode: firstSegment.carrier, size: 36 }), /* @__PURE__ */ import_react11.default.createElement("div", null, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontWeight: 600, fontSize: "14px" } }, getAirlineName3(firstSegment.carrier)), firstSegment.number && /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontSize: "12px", opacity: 0.85 } }, firstSegment.carrier, firstSegment.number))), firstSegment.from && lastSegment.to && kv("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", `${firstSegment.from} \u2192 ${lastSegment.to}`), firstSegment.departure && kv("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E2D\u0E2D\u0E01", formatThaiDateTime(firstSegment.departure)), lastSegment.arrival && kv("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E16\u0E36\u0E07", formatThaiDateTime(lastSegment.arrival)), flight.is_non_stop !== void 0 && kv("\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07", flight.is_non_stop ? "\u0E43\u0E0A\u0E48" : `\u0E41\u0E27\u0E30 ${flight.num_stops || 0} \u0E04\u0E23\u0E31\u0E49\u0E07`)), flight.currency && (flight.total_price != null || flight.price_total != null) && kv("\u0E23\u0E32\u0E04\u0E32\u0E44\u0E1F\u0E17\u0E4C\u0E1A\u0E34\u0E19", moneyThb(flight.total_price ?? flight.price_total, flight.currency)))), (hotelSegments.length > 0 || hotel.hotelName) && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F3E8} \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, hotelSegments.length > 0 ? (() => {
      const groupedHotels = {};
      hotelSegments.forEach((seg) => {
        const key = `${seg.hotelName || "Unknown"}-${seg.cityCode || seg.city || ""}`;
        if (!groupedHotels[key]) {
          groupedHotels[key] = {
            hotelName: seg.hotelName,
            hotelId: seg.hotelId,
            city: seg.city || seg.cityCode,
            address: seg.address,
            boardType: seg.boardType,
            currency: seg.currency || currency,
            nights: 0,
            price_total: 0,
            segments: []
          };
        }
        groupedHotels[key].nights += seg.nights || 0;
        const segPrice = seg.price_total || seg.price || 0;
        if (segPrice) {
          groupedHotels[key].price_total += segPrice;
        }
        groupedHotels[key].segments.push(seg);
      });
      const uniqueHotels = Object.values(groupedHotels);
      return uniqueHotels.map((grouped, idx) => /* @__PURE__ */ import_react11.default.createElement("div", { key: idx, style: { marginBottom: idx < uniqueHotels.length - 1 ? "12px" : "0" } }, grouped.city && kv("\u0E40\u0E21\u0E37\u0E2D\u0E07", grouped.city), grouped.hotelName && kv("\u0E0A\u0E37\u0E48\u0E2D\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21", grouped.hotelName), grouped.nights > 0 && kv("\u0E08\u0E33\u0E19\u0E27\u0E19\u0E04\u0E37\u0E19", `${grouped.nights} \u0E04\u0E37\u0E19`), grouped.boardType && kv("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E2D\u0E32\u0E2B\u0E32\u0E23", grouped.boardType), grouped.address && kv("\u0E17\u0E35\u0E48\u0E2D\u0E22\u0E39\u0E48", grouped.address), grouped.price_total > 0 && kv("\u0E23\u0E32\u0E04\u0E32", moneyThb(grouped.price_total, grouped.currency))));
    })() : /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, hotel.hotelName && kv("\u0E0A\u0E37\u0E48\u0E2D\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21", hotel.hotelName), hotel.nights != null && kv("\u0E08\u0E33\u0E19\u0E27\u0E19\u0E04\u0E37\u0E19", `${hotel.nights} \u0E04\u0E37\u0E19`), hotel.boardType && kv("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E2D\u0E32\u0E2B\u0E32\u0E23", hotel.boardType), hotel.address && kv("\u0E17\u0E35\u0E48\u0E2D\u0E22\u0E39\u0E48", hotel.address), hotel.price_total && kv("\u0E23\u0E32\u0E04\u0E32", moneyThb(hotel.price_total, hotel.currency || currency)), hotel.price && !hotel.price_total && kv("\u0E23\u0E32\u0E04\u0E32", moneyThb(hotel.price, hotel.currency || currency))))), (transportSegments.length > 0 || transport.type) && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F697} \u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, transportSegments.length > 0 ? transportSegments.map((seg, idx) => /* @__PURE__ */ import_react11.default.createElement("div", { key: idx, style: { marginBottom: idx < transportSegments.length - 1 ? "12px" : "0" } }, seg.type && kv(`\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17 (${idx + 1})`, seg.type), seg.route && kv("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", seg.route), seg.duration && kv("\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32", seg.duration), seg.price && kv("\u0E23\u0E32\u0E04\u0E32", moneyThb(seg.price, seg.currency || currency)))) : /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, transport.type && kv("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17", transport.type), transport.route && kv("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", transport.route), transport.duration && kv("\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32", transport.duration), (transport.price != null || transport.price_amount != null) && kv("\u0E23\u0E32\u0E04\u0E32", moneyThb(transport.price ?? transport.price_amount, transport.currency || currency))))), plan?.price_breakdown && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F4B0} \u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E23\u0E32\u0E04\u0E32"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, plan.price_breakdown.flight && kv("\u0E44\u0E1F\u0E17\u0E4C\u0E1A\u0E34\u0E19", moneyThb(plan.price_breakdown.flight, currency)), plan.price_breakdown.hotel && kv("\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01", moneyThb(plan.price_breakdown.hotel, currency)), plan.price_breakdown.transport && kv("\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07", moneyThb(plan.price_breakdown.transport, currency)), plan.price_breakdown.car && kv("\u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32", moneyThb(plan.price_breakdown.car, currency)))), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-footer" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-price" }, totalText || "\u2014"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "summary-note" }, "\u0E23\u0E32\u0E04\u0E32\u0E2D\u0E49\u0E32\u0E07\u0E2D\u0E34\u0E07\u0E08\u0E32\u0E01 Amadeus Search (production)", currency !== "THB" ? " \xB7 \u0E41\u0E2A\u0E14\u0E07\u0E40\u0E1B\u0E47\u0E19\u0E1A\u0E32\u0E17 (\u0E2D\u0E31\u0E15\u0E23\u0E32\u0E2D\u0E49\u0E32\u0E07\u0E2D\u0E34\u0E07)" : "")), cacheValidation && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section", style: {
      marginTop: "16px",
      padding: "12px",
      background: cacheValidation.valid ? "rgba(34, 197, 94, 0.1)" : "rgba(239, 68, 68, 0.1)",
      borderRadius: "8px",
      border: `1px solid ${cacheValidation.valid ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)"}`
    } }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title", style: {
      color: cacheValidation.valid ? "#22c55e" : "#ef4444",
      fontSize: "13px",
      fontWeight: 600
    } }, cacheValidation.valid ? "\u2705 \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E16\u0E39\u0E01\u0E15\u0E49\u0E2D\u0E07" : "\u26A0\uFE0F \u0E15\u0E23\u0E27\u0E08\u0E1E\u0E1A\u0E1B\u0E31\u0E0D\u0E2B\u0E32"), validationIssues.length > 0 && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px" } }, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontSize: "12px", fontWeight: 600, color: "#ef4444", marginBottom: "4px" } }, "\u0E1B\u0E31\u0E0D\u0E2B\u0E32:"), validationIssues.map((issue, idx) => /* @__PURE__ */ import_react11.default.createElement("div", { key: idx, style: { fontSize: "11px", color: "#dc2626", marginLeft: "8px" } }, "\u2022 ", issue))), validationWarnings.length > 0 && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px" } }, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontSize: "12px", fontWeight: 600, color: "#f59e0b", marginBottom: "4px" } }, "\u0E04\u0E33\u0E40\u0E15\u0E37\u0E2D\u0E19:"), validationWarnings.map((warning, idx) => /* @__PURE__ */ import_react11.default.createElement("div", { key: idx, style: { fontSize: "11px", color: "#d97706", marginLeft: "8px" } }, "\u2022 ", warning))), (cacheValidation.summary || effectiveSum) && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px", fontSize: "11px", color: "rgba(255, 255, 255, 0.7)" } }, cacheHasAny ? "\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E41\u0E04\u0E0A: " : "\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E40\u0E25\u0E37\u0E2D\u0E01: ", "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E02\u0E32\u0E44\u0E1B ", effectiveSum.flights_outbound ?? 0, ", \u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A ", effectiveSum.flights_inbound ?? 0, ", \u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 ", effectiveSum.ground_transport ?? 0, ", \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01 ", effectiveSum.accommodation ?? 0)));
  }
  function isLocationInThailand(loc) {
    if (!loc || typeof loc !== "string") return false;
    const s = loc.toLowerCase().trim();
    const thaiDomestic = [
      "bangkok",
      "bkk",
      "dmk",
      "\u0E01\u0E23\u0E38\u0E07\u0E40\u0E17\u0E1E",
      "don mueang",
      "suvarnabhumi",
      "chiang mai",
      "cnx",
      "\u0E40\u0E0A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48",
      "phuket",
      "hkt",
      "\u0E20\u0E39\u0E40\u0E01\u0E47\u0E15",
      "krabi",
      "kbv",
      "\u0E01\u0E23\u0E30\u0E1A\u0E35\u0E48",
      "samui",
      "usm",
      "\u0E2A\u0E21\u0E38\u0E22",
      "koh samui",
      "hat yai",
      "hdj",
      "\u0E2B\u0E32\u0E14\u0E43\u0E2B\u0E0D\u0E48",
      "udon thani",
      "uth",
      "udon",
      "\u0E2D\u0E38\u0E14\u0E23",
      "khon kaen",
      "kkc",
      "\u0E02\u0E2D\u0E19\u0E41\u0E01\u0E48\u0E19",
      "ubon ratchathani",
      "ubn",
      "\u0E2D\u0E38\u0E1A\u0E25",
      "nakhon si thammarat",
      "nst",
      "\u0E19\u0E04\u0E23\u0E28\u0E23\u0E35\u0E18\u0E23\u0E23\u0E21\u0E23\u0E32\u0E0A",
      "surat thani",
      "urt",
      "\u0E2A\u0E38\u0E23\u0E32\u0E29\u0E0E\u0E23\u0E4C",
      "pattaya",
      "utapao",
      "utm",
      "\u0E1E\u0E31\u0E17\u0E22\u0E32",
      "chiang rai",
      "cei",
      "\u0E40\u0E0A\u0E35\u0E22\u0E07\u0E23\u0E32\u0E22",
      "lampang",
      "lpi",
      "\u0E25\u0E33\u0E1B\u0E32\u0E07",
      "phitsanulok",
      "phs",
      "\u0E1E\u0E34\u0E29\u0E13\u0E38\u0E42\u0E25\u0E01"
    ];
    return thaiDomestic.some((key) => s.includes(key) || s === key);
  }
  function UserInfoCard({ userProfile, onEdit, isDomesticTravel = false }) {
    const hasRequiredInfo = userProfile && (userProfile.first_name && userProfile.last_name && userProfile.email && userProfile.phone);
    const hasPassportInfo = userProfile && (userProfile.passport_no && userProfile.passport_expiry && userProfile.nationality);
    const showPassportSection = !isDomesticTravel;
    const maskPassportNumber = (passportNo) => {
      if (!passportNo || typeof passportNo !== "string") return "\u2014";
      const trimmed = passportNo.trim();
      if (trimmed.length <= 3) return "*".repeat(trimmed.length);
      const visible = trimmed.slice(-3);
      const masked = "*".repeat(Math.max(trimmed.length - 3, 3));
      return `${masked}${visible}`;
    };
    const readyToBook = hasRequiredInfo && (isDomesticTravel || hasPassportInfo);
    return /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card plan-card-summary" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-title" }, /* @__PURE__ */ import_react11.default.createElement("span", { className: "plan-card-label" }, "\u{1F464} \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1C\u0E39\u0E49\u0E43\u0E0A\u0E49\u0E2A\u0E33\u0E2B\u0E23\u0E31\u0E1A\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07"))), !userProfile ? /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, /* @__PURE__ */ import_react11.default.createElement("div", null, "\u26A0\uFE0F \u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49\u0E01\u0E23\u0E2D\u0E01\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1C\u0E39\u0E49\u0E43\u0E0A\u0E49"), /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px" } }, isDomesticTravel ? "\u0E01\u0E23\u0E38\u0E13\u0E32\u0E01\u0E23\u0E2D\u0E01\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E01\u0E48\u0E2D\u0E19\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E08\u0E2D\u0E07 (\u0E0A\u0E37\u0E48\u0E2D, \u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25, \u0E2D\u0E35\u0E40\u0E21\u0E25, \u0E40\u0E1A\u0E2D\u0E23\u0E4C\u0E42\u0E17\u0E23)" : "\u0E01\u0E23\u0E38\u0E13\u0E32\u0E01\u0E23\u0E2D\u0E01\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E01\u0E48\u0E2D\u0E19\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E08\u0E2D\u0E07 (\u0E0A\u0E37\u0E48\u0E2D, \u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25, \u0E2D\u0E35\u0E40\u0E21\u0E25, \u0E40\u0E1A\u0E2D\u0E23\u0E4C\u0E42\u0E17\u0E23, \u0E1E\u0E32\u0E2A\u0E1B\u0E2D\u0E23\u0E4C\u0E15)"))) : /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1E\u0E37\u0E49\u0E19\u0E10\u0E32\u0E19"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, kv("\u0E0A\u0E37\u0E48\u0E2D (\u0E44\u0E17\u0E22)", userProfile.first_name_th || "\u2014"), kv("\u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25 (\u0E44\u0E17\u0E22)", userProfile.last_name_th || "\u2014"), kv("\u0E0A\u0E37\u0E48\u0E2D (EN)", userProfile.first_name || "\u2014"), kv("\u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25 (EN)", userProfile.last_name || "\u2014"), userProfile.national_id && kv("\u0E40\u0E25\u0E02\u0E1A\u0E31\u0E15\u0E23\u0E1B\u0E23\u0E30\u0E0A\u0E32\u0E0A\u0E19", userProfile.national_id), kv("\u0E2D\u0E35\u0E40\u0E21\u0E25", userProfile.email || "\u2014"), kv("\u0E40\u0E1A\u0E2D\u0E23\u0E4C\u0E42\u0E17\u0E23", userProfile.phone || "\u2014"), kv("\u0E27\u0E31\u0E19\u0E40\u0E01\u0E34\u0E14", userProfile.dob ? formatDateThai(userProfile.dob) : "\u2014"), kv("\u0E40\u0E1E\u0E28", userProfile.gender || "\u2014"))), Array.isArray(userProfile.family) && userProfile.family.length > 0 && userProfile.family.map((member, index) => /* @__PURE__ */ import_react11.default.createElement("div", { key: member.id || `family-${index}`, className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F465} \u0E1C\u0E39\u0E49\u0E08\u0E2D\u0E07\u0E23\u0E48\u0E27\u0E21 ", index + 1, " ", member.type === "child" ? "(\u0E40\u0E14\u0E47\u0E01)" : "(\u0E1C\u0E39\u0E49\u0E43\u0E2B\u0E0D\u0E48)"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, kv("\u0E0A\u0E37\u0E48\u0E2D (\u0E44\u0E17\u0E22)", member.first_name_th || "\u2014"), kv("\u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25 (\u0E44\u0E17\u0E22)", member.last_name_th || "\u2014"), kv("\u0E0A\u0E37\u0E48\u0E2D (EN)", member.first_name || "\u2014"), kv("\u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25 (EN)", member.last_name || "\u2014"), member.national_id && kv("\u0E40\u0E25\u0E02\u0E1A\u0E31\u0E15\u0E23\u0E1B\u0E23\u0E30\u0E0A\u0E32\u0E0A\u0E19", member.national_id), kv("\u0E27\u0E31\u0E19\u0E40\u0E01\u0E34\u0E14", member.date_of_birth ? formatDateThai(member.date_of_birth) : "\u2014"), kv("\u0E40\u0E1E\u0E28", member.gender || "\u2014")), showPassportSection && (member.passport_no || member.passport_expiry || member.passports && member.passports.length > 0) && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body", style: { marginTop: "8px", paddingTop: "8px", borderTop: "1px solid rgba(0,0,0,0.06)" } }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-small", style: { marginBottom: "6px", fontWeight: 600, color: "#374151" } }, "\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1E\u0E32\u0E2A\u0E1B\u0E2D\u0E23\u0E4C\u0E15"), member.passports && member.passports.length > 0 ? (member.primary_passport || member.passports[0]).passport_no && /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, kv("\u0E40\u0E25\u0E02\u0E1E\u0E32\u0E2A\u0E1B\u0E2D\u0E23\u0E4C\u0E15", maskPassportNumber((member.primary_passport || member.passports[0]).passport_no)), kv("\u0E27\u0E31\u0E19\u0E2B\u0E21\u0E14\u0E2D\u0E32\u0E22\u0E38", (member.primary_passport || member.passports[0]).passport_expiry ? formatDateThai((member.primary_passport || member.passports[0]).passport_expiry) : "\u2014"), (member.primary_passport || member.passports[0]).nationality && kv("\u0E2A\u0E31\u0E0D\u0E0A\u0E32\u0E15\u0E34", (member.primary_passport || member.passports[0]).nationality)) : /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, kv("\u0E40\u0E25\u0E02\u0E1E\u0E32\u0E2A\u0E1B\u0E2D\u0E23\u0E4C\u0E15", member.passport_no ? maskPassportNumber(member.passport_no) : "\u2014"), kv("\u0E27\u0E31\u0E19\u0E2B\u0E21\u0E14\u0E2D\u0E32\u0E22\u0E38", member.passport_expiry ? formatDateThai(member.passport_expiry) : "\u2014"), member.nationality && kv("\u0E2A\u0E31\u0E0D\u0E0A\u0E32\u0E15\u0E34", member.nationality), member.passport_issue_date && kv("\u0E27\u0E31\u0E19\u0E2D\u0E2D\u0E01\u0E2B\u0E19\u0E31\u0E07\u0E2A\u0E37\u0E2D\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07", formatDateThai(member.passport_issue_date)), member.passport_given_names && kv("\u0E0A\u0E37\u0E48\u0E2D\u0E15\u0E32\u0E21\u0E2B\u0E19\u0E31\u0E07\u0E2A\u0E37\u0E2D\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 (EN)", member.passport_given_names), member.passport_surname && kv("\u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25\u0E15\u0E32\u0E21\u0E2B\u0E19\u0E31\u0E07\u0E2A\u0E37\u0E2D\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 (EN)", member.passport_surname))))), showPassportSection && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1E\u0E32\u0E2A\u0E1B\u0E2D\u0E23\u0E4C\u0E15"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, kv("\u0E40\u0E25\u0E02\u0E1E\u0E32\u0E2A\u0E1B\u0E2D\u0E23\u0E4C\u0E15", userProfile.passport_no ? maskPassportNumber(userProfile.passport_no) : "\u2014"), kv("\u0E27\u0E31\u0E19\u0E2B\u0E21\u0E14\u0E2D\u0E32\u0E22\u0E38", userProfile.passport_expiry ? formatDateThai(userProfile.passport_expiry) : "\u2014"), kv("\u0E2A\u0E31\u0E0D\u0E0A\u0E32\u0E15\u0E34", userProfile.nationality || "\u2014"), userProfile.passport_issue_date && kv("\u0E27\u0E31\u0E19\u0E2D\u0E2D\u0E01\u0E2B\u0E19\u0E31\u0E07\u0E2A\u0E37\u0E2D\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07", formatDateThai(userProfile.passport_issue_date)), userProfile.passport_issuing_country && kv("\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28\u0E17\u0E35\u0E48\u0E2D\u0E2D\u0E01\u0E2B\u0E19\u0E31\u0E07\u0E2A\u0E37\u0E2D\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07", userProfile.passport_issuing_country), userProfile.passport_given_names && kv("\u0E0A\u0E37\u0E48\u0E2D\u0E15\u0E32\u0E21\u0E2B\u0E19\u0E31\u0E07\u0E2A\u0E37\u0E2D\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 (EN)", userProfile.passport_given_names), userProfile.passport_surname && kv("\u0E19\u0E32\u0E21\u0E2A\u0E01\u0E38\u0E25\u0E15\u0E32\u0E21\u0E2B\u0E19\u0E31\u0E07\u0E2A\u0E37\u0E2D\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 (EN)", userProfile.passport_surname), userProfile.place_of_birth && kv("\u0E2A\u0E16\u0E32\u0E19\u0E17\u0E35\u0E48\u0E40\u0E01\u0E34\u0E14", userProfile.place_of_birth)), !hasPassportInfo && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-small", style: { marginTop: "8px", opacity: 0.8 } }, "\u26A0\uFE0F \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1E\u0E32\u0E2A\u0E1B\u0E2D\u0E23\u0E4C\u0E15\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E04\u0E23\u0E1A")), userProfile.visa_type && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F6C2} \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E27\u0E35\u0E0B\u0E48\u0E32"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, kv("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E27\u0E35\u0E0B\u0E48\u0E32", userProfile.visa_type || "\u2014"), kv("\u0E40\u0E25\u0E02\u0E17\u0E35\u0E48\u0E27\u0E35\u0E0B\u0E48\u0E32", userProfile.visa_number || "\u2014"), kv("\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28\u0E17\u0E35\u0E48\u0E2D\u0E2D\u0E01\u0E27\u0E35\u0E0B\u0E48\u0E32", userProfile.visa_issuing_country || "\u2014"), kv("\u0E27\u0E31\u0E19\u0E2D\u0E2D\u0E01\u0E27\u0E35\u0E0B\u0E48\u0E32", userProfile.visa_issue_date ? formatDateThai(userProfile.visa_issue_date) : "\u2014"), kv("\u0E27\u0E31\u0E19\u0E2B\u0E21\u0E14\u0E2D\u0E32\u0E22\u0E38\u0E27\u0E35\u0E0B\u0E48\u0E32", userProfile.visa_expiry_date ? formatDateThai(userProfile.visa_expiry_date) : "\u2014"), kv("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E01\u0E32\u0E23\u0E40\u0E02\u0E49\u0E32\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28", userProfile.visa_entry_type === "S" ? "\u0E04\u0E23\u0E31\u0E49\u0E07\u0E40\u0E14\u0E35\u0E22\u0E27 (Single Entry)" : userProfile.visa_entry_type === "M" ? "\u0E2B\u0E25\u0E32\u0E22\u0E04\u0E23\u0E31\u0E49\u0E07 (Multiple Entry)" : userProfile.visa_entry_type || "\u2014"), kv("\u0E27\u0E31\u0E15\u0E16\u0E38\u0E1B\u0E23\u0E30\u0E2A\u0E07\u0E04\u0E4C", userProfile.visa_purpose === "T" ? "\u0E17\u0E48\u0E2D\u0E07\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27" : userProfile.visa_purpose === "B" ? "\u0E18\u0E38\u0E23\u0E01\u0E34\u0E08" : userProfile.visa_purpose === "S" ? "\u0E28\u0E36\u0E01\u0E29\u0E32" : userProfile.visa_purpose === "W" ? "\u0E17\u0E33\u0E07\u0E32\u0E19" : userProfile.visa_purpose === "TR" ? "\u0E1C\u0E48\u0E32\u0E19\u0E17\u0E32\u0E07" : userProfile.visa_purpose === "O" ? "\u0E2D\u0E37\u0E48\u0E19\u0E46" : userProfile.visa_purpose || "\u2014"))), (userProfile.emergency_contact_name || userProfile.emergency_contact_phone || userProfile.hotel_number_of_guests) && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u{1F3E8} \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E2A\u0E33\u0E2B\u0E23\u0E31\u0E1A\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body" }, (userProfile.emergency_contact_name || userProfile.emergency_contact_phone) && /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontWeight: 600, marginTop: "8px", marginBottom: "4px", color: "#1e40af" } }, "\u{1F4DE} \u0E15\u0E34\u0E14\u0E15\u0E48\u0E2D\u0E09\u0E38\u0E01\u0E40\u0E09\u0E34\u0E19"), userProfile.emergency_contact_name && kv("\u0E0A\u0E37\u0E48\u0E2D", userProfile.emergency_contact_name), userProfile.emergency_contact_phone && kv("\u0E40\u0E1A\u0E2D\u0E23\u0E4C\u0E42\u0E17\u0E23", userProfile.emergency_contact_phone), userProfile.emergency_contact_relation && kv(
      "\u0E04\u0E27\u0E32\u0E21\u0E2A\u0E31\u0E21\u0E1E\u0E31\u0E19\u0E18\u0E4C",
      userProfile.emergency_contact_relation === "SPOUSE" ? "\u0E04\u0E39\u0E48\u0E2A\u0E21\u0E23\u0E2A" : userProfile.emergency_contact_relation === "PARENT" ? "\u0E1A\u0E34\u0E14\u0E32/\u0E21\u0E32\u0E23\u0E14\u0E32" : userProfile.emergency_contact_relation === "FRIEND" ? "\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E19" : userProfile.emergency_contact_relation === "OTHER" ? "\u0E2D\u0E37\u0E48\u0E19\u0E46" : userProfile.emergency_contact_relation
    ), userProfile.emergency_contact_email && kv("\u0E2D\u0E35\u0E40\u0E21\u0E25", userProfile.emergency_contact_email)), userProfile.hotel_number_of_guests && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "12px" } }, kv("\u0E08\u0E33\u0E19\u0E27\u0E19\u0E1C\u0E39\u0E49\u0E40\u0E02\u0E49\u0E32\u0E1E\u0E31\u0E01", `${userProfile.hotel_number_of_guests} \u0E04\u0E19`))))));
  }
  function ConfirmBookingCard({ canBook, onConfirm, onPayment, note, isBooking, bookingResult, chatMode = "normal", agentState = null, onNavigateToBookings = null, existingBookingForTrip = false }) {
    const needsPayment = bookingResult?.needs_payment || bookingResult?.status === "pending_payment";
    const isConfirmed = bookingResult?.status === "confirmed" || bookingResult?.status === "paid";
    const isAlreadyBooked = existingBookingForTrip || bookingResult && !bookingResult.ok && bookingResult.already_booked === true;
    const isAgentMode = chatMode === "agent";
    const isAutoBooked = isAgentMode && (bookingResult?.auto_booked || bookingResult?.status === "pending_payment" || bookingResult?.status === "confirmed" || agentState?.intent === "booking" || agentState?.step === "completed" || agentState?.step === "pending_payment" || agentState?.step === "booking");
    const isAutoBookingInProgress = isAgentMode && !bookingResult && !isAutoBooked && canBook;
    return /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card plan-card-summary" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-header" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-title" }, /* @__PURE__ */ import_react11.default.createElement("span", { className: "plan-card-label" }, "\u2705 \u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E08\u0E2D\u0E07"), (needsPayment || isConfirmed) && !isAlreadyBooked && /* @__PURE__ */ import_react11.default.createElement("span", { className: "plan-card-tag" }, needsPayment ? "\u0E23\u0E2D\u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19" : "\u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08"), isAlreadyBooked && /* @__PURE__ */ import_react11.default.createElement("span", { className: "plan-card-tag", style: { background: "#fef3c7", color: "#92400e" } }, "\u0E08\u0E2D\u0E07\u0E44\u0E1B\u0E41\u0E25\u0E49\u0E27"))), isBooking ? /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, /* @__PURE__ */ import_react11.default.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px" } }, /* @__PURE__ */ import_react11.default.createElement("span", { className: "plan-card-spinner" }), /* @__PURE__ */ import_react11.default.createElement("span", null, "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E14\u0E33\u0E40\u0E19\u0E34\u0E19\u0E01\u0E32\u0E23...")), /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px", opacity: 0.8 } }, needsPayment ? "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E23\u0E49\u0E32\u0E07\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07..." : "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E41\u0E25\u0E30\u0E08\u0E2D\u0E07..."))) : bookingResult && isAlreadyBooked ? /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title", style: { color: "#92400e" } }, "\u{1F4CB} \u0E08\u0E2D\u0E07\u0E44\u0E1B\u0E41\u0E25\u0E49\u0E27"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, /* @__PURE__ */ import_react11.default.createElement("p", { style: { margin: 0 } }, bookingResult.message), onNavigateToBookings && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-footer summary-footer", style: { marginTop: "16px" } }, /* @__PURE__ */ import_react11.default.createElement(
      "button",
      {
        type: "button",
        className: "plan-card-button",
        style: { background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)" },
        onClick: onNavigateToBookings
      },
      "\u{1F4CB} \u0E44\u0E1B\u0E17\u0E35\u0E48 My Bookings"
    )))) : existingBookingForTrip ? /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title", style: { color: "#92400e" } }, "\u{1F4CB} \u0E08\u0E2D\u0E07\u0E44\u0E1B\u0E41\u0E25\u0E49\u0E27"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, /* @__PURE__ */ import_react11.default.createElement("p", { style: { margin: 0 } }, "\u0E17\u0E23\u0E34\u0E1B\u0E19\u0E35\u0E49\u0E21\u0E35\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E2D\u0E22\u0E39\u0E48\u0E41\u0E25\u0E49\u0E27 \u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E01\u0E14\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E08\u0E2D\u0E07\u0E0B\u0E49\u0E33\u0E44\u0E14\u0E49"), onNavigateToBookings && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-footer summary-footer", style: { marginTop: "16px" } }, /* @__PURE__ */ import_react11.default.createElement(
      "button",
      {
        type: "button",
        className: "plan-card-button",
        style: { background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)" },
        onClick: onNavigateToBookings
      },
      "\u{1F4CB} \u0E44\u0E1B\u0E17\u0E35\u0E48 My Bookings"
    )))) : bookingResult ? /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, bookingResult.ok ? needsPayment ? "\u2705 \u0E2A\u0E23\u0E49\u0E32\u0E07\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08" : "\u2705 \u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08" : "\u274C \u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, bookingResult.message && /* @__PURE__ */ import_react11.default.createElement("div", null, typeof bookingResult.message === "string" ? bookingResult.message : JSON.stringify(bookingResult.message)), needsPayment && bookingResult.total_price && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "12px", padding: "12px", background: "#f0f9ff", borderRadius: "8px" } }, /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontWeight: 600, marginBottom: "8px" } }, "\u{1F4B0} \u0E23\u0E32\u0E04\u0E32\u0E23\u0E27\u0E21"), /* @__PURE__ */ import_react11.default.createElement("div", { style: { fontSize: "20px", fontWeight: 700, color: "#1e40af" } }, moneyThb(bookingResult.total_price, bookingResult.currency) || new Intl.NumberFormat("th-TH", { style: "currency", currency: "THB", minimumFractionDigits: 0 }).format(bookingResult.total_price))), bookingResult.booking_reference && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "12px" } }, /* @__PURE__ */ import_react11.default.createElement("strong", null, "\u{1F4CB} \u0E2B\u0E21\u0E32\u0E22\u0E40\u0E25\u0E02\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07:"), " ", bookingResult.booking_reference), bookingResult.detail && /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px", opacity: 0.8 } }, typeof bookingResult.detail === "string" ? bookingResult.detail : JSON.stringify(bookingResult.detail)), needsPayment && bookingResult.booking_id && onPayment && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-footer summary-footer", style: { marginTop: "16px" } }, /* @__PURE__ */ import_react11.default.createElement(
      "button",
      {
        className: "plan-card-button",
        style: { background: "linear-gradient(135deg, #10b981 0%, #059669 100%)" },
        onClick: () => onPayment(bookingResult.booking_id),
        disabled: isBooking
      },
      "\u{1F4B3} \u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E41\u0E25\u0E30\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E08\u0E2D\u0E07"
    )))) : /* @__PURE__ */ import_react11.default.createElement(import_react11.default.Fragment, null, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section" }, /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-title" }, "\u0E04\u0E27\u0E32\u0E21\u0E1B\u0E25\u0E2D\u0E14\u0E20\u0E31\u0E22"), /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-section-body plan-card-small" }, /* @__PURE__ */ import_react11.default.createElement("div", null, "\u{1F512} \u0E23\u0E30\u0E1A\u0E1A\u0E25\u0E47\u0E2D\u0E01\u0E43\u0E2B\u0E49\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E40\u0E09\u0E1E\u0E32\u0E30 Amadeus Sandbox (test) \u0E40\u0E17\u0E48\u0E32\u0E19\u0E31\u0E49\u0E19"), /* @__PURE__ */ import_react11.default.createElement("div", { style: { marginTop: "8px" } }, "\u26A0\uFE0F \u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E19\u0E35\u0E49\u0E40\u0E1B\u0E47\u0E19\u0E01\u0E32\u0E23\u0E17\u0E14\u0E2A\u0E2D\u0E1A\u0E40\u0E17\u0E48\u0E32\u0E19\u0E31\u0E49\u0E19 \u0E44\u0E21\u0E48\u0E43\u0E0A\u0E48\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E08\u0E23\u0E34\u0E07"), note && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-small", style: { marginTop: "8px" } }, note))), !isAutoBooked && !isAutoBookingInProgress && !existingBookingForTrip && /* @__PURE__ */ import_react11.default.createElement("div", { className: "plan-card-footer summary-footer" }, /* @__PURE__ */ import_react11.default.createElement(
      "button",
      {
        className: `plan-card-button ${!canBook ? "summary-disabled" : ""}`,
        disabled: !canBook || isBooking,
        onClick: onConfirm
      },
      "\u2705 \u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07"
    ))));
  }

  // src/components/chat/SlotCards.jsx
  var import_react12 = __toESM(require_react(), 1);
  function moneyThb2(amount, sourceCurrency) {
    return formatPriceInThb(amount, sourceCurrency || "THB");
  }
  function safeText2(v) {
    if (v == null) return "";
    return String(v);
  }
  function kv2(label, value) {
    const v = safeText2(value).trim();
    return /* @__PURE__ */ import_react12.default.createElement("div", { className: "summary-kv" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "summary-k" }, label), /* @__PURE__ */ import_react12.default.createElement("div", { className: "summary-v" }, v || "\u2014"));
  }
  function formatThaiDateTime2(isoDateTime) {
    if (!isoDateTime) return "";
    try {
      const date = new Date(isoDateTime);
      if (isNaN(date.getTime())) return isoDateTime;
      const day = date.getDate();
      const month = date.getMonth() + 1;
      const year = date.getFullYear() + 543;
      const hours = String(date.getHours()).padStart(2, "0");
      const minutes = String(date.getMinutes()).padStart(2, "0");
      return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch (e) {
      return isoDateTime;
    }
  }
  function getAirlineName4(code) {
    if (!code) return "Unknown";
    return AIRLINE_NAMES[code.toUpperCase()] || code;
  }
  function FlightSlotCard({ flight, travelSlots }) {
    if (!flight) {
      return /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-header" }, /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-title" }, "\u2708\uFE0F \u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19"), /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-status" }, "\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49\u0E40\u0E25\u0E37\u0E2D\u0E01")), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-body" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-empty" }, '\u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E43\u0E19\u0E41\u0E0A\u0E17\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19 \u0E40\u0E0A\u0E48\u0E19 "\u0E02\u0E2D\u0E44\u0E1F\u0E25\u0E15\u0E4C\u0E40\u0E0A\u0E49\u0E32\u0E01\u0E27\u0E48\u0E32\u0E19\u0E35\u0E49"')));
    }
    const segments = dedupeSegments(flight.segments || []);
    const currency = flight.currency || "THB";
    const firstSegment = segments[0];
    const lastSegment = segments[segments.length - 1];
    return /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-header" }, /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-title" }, "\u2708\uFE0F \u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19"), /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-status selected" }, "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E41\u0E25\u0E49\u0E27")), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-body" }, firstSegment && lastSegment && /* @__PURE__ */ import_react12.default.createElement(import_react12.default.Fragment, null, kv2("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", `${firstSegment.from || ""} \u2192 ${lastSegment.to || ""}`), (firstSegment.departure || firstSegment.depart_at) && kv2("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E2D\u0E2D\u0E01", formatThaiDateTime2(firstSegment.departure || firstSegment.depart_at)), (lastSegment.arrival || lastSegment.arrive_at) && kv2("\u0E27\u0E31\u0E19-\u0E40\u0E27\u0E25\u0E32\u0E16\u0E36\u0E07", formatThaiDateTime2(lastSegment.arrival || lastSegment.arrive_at)), firstSegment.carrier && kv2("\u0E2A\u0E32\u0E22\u0E01\u0E32\u0E23\u0E1A\u0E34\u0E19", getAirlineName4(firstSegment.carrier)), flight.total_duration && kv2("\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32\u0E1A\u0E34\u0E19", flight.total_duration), flight.is_non_stop !== void 0 && kv2("\u0E1A\u0E34\u0E19\u0E15\u0E23\u0E07", flight.is_non_stop ? "\u0E43\u0E0A\u0E48" : `\u0E41\u0E27\u0E30 ${flight.num_stops || 0} \u0E04\u0E23\u0E31\u0E49\u0E07`), (flight.total_price != null || flight.price_total != null) && kv2("\u0E23\u0E32\u0E04\u0E32", moneyThb2(flight.total_price ?? flight.price_total, currency))), segments.length > 1 && /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-segments" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-segments-title" }, "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14 (", segments.length, " segments):"), segments.map((seg, idx) => /* @__PURE__ */ import_react12.default.createElement("div", { key: idx, className: "slot-card-segment" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "segment-number" }, "Segment ", idx + 1), seg.from && seg.to && /* @__PURE__ */ import_react12.default.createElement("div", null, seg.from, " \u2192 ", seg.to), (seg.departure || seg.depart_at) && /* @__PURE__ */ import_react12.default.createElement("div", null, "\u0E2D\u0E2D\u0E01: ", formatThaiDateTime2(seg.departure || seg.depart_at)), (seg.arrival || seg.arrive_at) && /* @__PURE__ */ import_react12.default.createElement("div", null, "\u0E16\u0E36\u0E07: ", formatThaiDateTime2(seg.arrival || seg.arrive_at)), seg.carrier && /* @__PURE__ */ import_react12.default.createElement("div", null, "\u0E2A\u0E32\u0E22\u0E01\u0E32\u0E23\u0E1A\u0E34\u0E19: ", getAirlineName4(seg.carrier))))), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-edit-hint" }, '\u{1F4A1} \u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E43\u0E19\u0E41\u0E0A\u0E17\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E41\u0E01\u0E49\u0E44\u0E02 \u0E40\u0E0A\u0E48\u0E19 "\u0E02\u0E2D\u0E44\u0E1F\u0E25\u0E15\u0E4C\u0E40\u0E0A\u0E49\u0E32\u0E01\u0E27\u0E48\u0E32\u0E19\u0E35\u0E49" \u0E2B\u0E23\u0E37\u0E2D "\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E2A\u0E32\u0E22\u0E01\u0E32\u0E23\u0E1A\u0E34\u0E19"')));
  }
  function HotelSlotCard({ hotel, travelSlots }) {
    if (!hotel) {
      return /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-header" }, /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-title" }, "\u{1F3E8} \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01"), /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-status" }, "\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49\u0E40\u0E25\u0E37\u0E2D\u0E01")), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-body" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-empty" }, '\u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E43\u0E19\u0E41\u0E0A\u0E17\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01 \u0E40\u0E0A\u0E48\u0E19 "\u0E02\u0E2D\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01\u0E16\u0E39\u0E01\u0E25\u0E07"')));
    }
    const hotelSegments = hotel.segments || [];
    const currency = hotel.currency || "THB";
    return /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-header" }, /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-title" }, "\u{1F3E8} \u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01"), /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-status selected" }, "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E41\u0E25\u0E49\u0E27")), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-body" }, hotelSegments.length > 0 ? /* @__PURE__ */ import_react12.default.createElement(import_react12.default.Fragment, null, hotelSegments.map((seg, idx) => /* @__PURE__ */ import_react12.default.createElement("div", { key: idx, className: "slot-card-segment" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "segment-number" }, "\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01 ", idx + 1), seg.city && kv2("\u0E40\u0E21\u0E37\u0E2D\u0E07", seg.city), seg.nights && kv2("\u0E08\u0E33\u0E19\u0E27\u0E19\u0E04\u0E37\u0E19", `${seg.nights} \u0E04\u0E37\u0E19`), seg.hotelName && kv2("\u0E0A\u0E37\u0E48\u0E2D\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21", seg.hotelName), seg.boardType && kv2("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E2D\u0E32\u0E2B\u0E32\u0E23", seg.boardType), seg.address && kv2("\u0E17\u0E35\u0E48\u0E2D\u0E22\u0E39\u0E48", seg.address), seg.price && kv2("\u0E23\u0E32\u0E04\u0E32", moneyThb2(seg.price, seg.currency || currency))))) : /* @__PURE__ */ import_react12.default.createElement(import_react12.default.Fragment, null, hotel.hotelName && kv2("\u0E0A\u0E37\u0E48\u0E2D\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21", hotel.hotelName), hotel.city && kv2("\u0E40\u0E21\u0E37\u0E2D\u0E07", hotel.city), hotel.nights && kv2("\u0E08\u0E33\u0E19\u0E27\u0E19\u0E04\u0E37\u0E19", `${hotel.nights} \u0E04\u0E37\u0E19`), hotel.boardType && kv2("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E2D\u0E32\u0E2B\u0E32\u0E23", hotel.boardType), hotel.address && kv2("\u0E17\u0E35\u0E48\u0E2D\u0E22\u0E39\u0E48", hotel.address), (hotel.total_price != null || hotel.price_total != null) && kv2("\u0E23\u0E32\u0E04\u0E32", moneyThb2(hotel.total_price ?? hotel.price_total, currency))), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-edit-hint" }, '\u{1F4A1} \u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E43\u0E19\u0E41\u0E0A\u0E17\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E41\u0E01\u0E49\u0E44\u0E02 \u0E40\u0E0A\u0E48\u0E19 "\u0E02\u0E2D\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01\u0E16\u0E39\u0E01\u0E25\u0E07" \u0E2B\u0E23\u0E37\u0E2D "\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21"')));
  }
  function TransportSlotCard({ transport }) {
    if (!transport || !transport.type && (!transport.segments || transport.segments.length === 0)) {
      return /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-header" }, /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-title" }, "\u{1F697} \u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-status" }, "\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E44\u0E14\u0E49\u0E40\u0E25\u0E37\u0E2D\u0E01")), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-body" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-empty" }, '\u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E43\u0E19\u0E41\u0E0A\u0E17\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07 \u0E40\u0E0A\u0E48\u0E19 "\u0E02\u0E2D\u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32"')));
    }
    const transportSegments = transport.segments || [];
    const currency = transport.currency || transport.data?.currency || "THB";
    const getPrice = (item) => {
      return item?.price || item?.price_amount || item?.data?.price || item?.data?.price_amount || null;
    };
    const formatDuration4 = (durationStr) => {
      if (!durationStr) return null;
      if (typeof durationStr === "string" && durationStr.startsWith("PT")) {
        let hours = 0, minutes = 0;
        const hourMatch = durationStr.match(/(\d+)H/);
        const minuteMatch = durationStr.match(/(\d+)M/);
        if (hourMatch) hours = parseInt(hourMatch[1]);
        if (minuteMatch) minutes = parseInt(minuteMatch[1]);
        const parts = [];
        if (hours > 0) parts.push(`${hours} \u0E0A\u0E31\u0E48\u0E27\u0E42\u0E21\u0E07`);
        if (minutes > 0) parts.push(`${minutes} \u0E19\u0E32\u0E17\u0E35`);
        return parts.length > 0 ? parts.join(" ") : durationStr;
      }
      return durationStr;
    };
    return /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card" }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-header" }, /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-title" }, transport.type === "car_rental" ? "\u{1F697} \u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32" : transport.type === "bus" ? "\u{1F68C} \u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23" : transport.type === "train" ? "\u{1F682} \u0E23\u0E16\u0E44\u0E1F" : transport.type === "metro" ? "\u{1F687} \u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32" : transport.type === "ferry" ? "\u26F4\uFE0F \u0E40\u0E23\u0E37\u0E2D" : transport.type === "transfer" ? "\u{1F697} \u0E23\u0E16\u0E23\u0E31\u0E1A\u0E2A\u0E48\u0E07" : "\u{1F697} \u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07"), /* @__PURE__ */ import_react12.default.createElement("span", { className: "slot-card-status selected" }, "\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E41\u0E25\u0E49\u0E27")), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-body" }, transportSegments.length > 0 ? /* @__PURE__ */ import_react12.default.createElement(import_react12.default.Fragment, null, transportSegments.map((seg, idx) => {
      const segmentPrice = getPrice(seg);
      const segmentCurrency = seg.currency || seg.data?.currency || currency;
      return /* @__PURE__ */ import_react12.default.createElement("div", { key: idx, className: "slot-card-segment", style: {
        marginBottom: "16px",
        padding: "12px",
        background: "rgba(255, 255, 255, 0.05)",
        borderRadius: "8px",
        border: "1px solid rgba(255, 255, 255, 0.1)"
      } }, /* @__PURE__ */ import_react12.default.createElement("div", { className: "segment-number", style: { fontWeight: "600", marginBottom: "8px", fontSize: "14px" } }, "Segment ", idx + 1), seg.type && kv2("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17", seg.type === "car_rental" ? "\u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32" : seg.type === "bus" ? "\u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23" : seg.type === "train" ? "\u0E23\u0E16\u0E44\u0E1F" : seg.type === "metro" ? "\u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32" : seg.type === "ferry" ? "\u0E40\u0E23\u0E37\u0E2D" : seg.type === "transfer" ? "\u0E23\u0E16\u0E23\u0E31\u0E1A\u0E2A\u0E48\u0E07" : seg.type), seg.route && kv2("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", seg.route), (seg.from || seg.origin) && (seg.to || seg.destination) && !seg.route && kv2("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", `${seg.from || seg.origin} \u2192 ${seg.to || seg.destination}`), (seg.duration || seg.data?.duration) && kv2("\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32", formatDuration4(seg.duration || seg.data?.duration)), (seg.distance || seg.data?.distance) && kv2("\u0E23\u0E30\u0E22\u0E30\u0E17\u0E32\u0E07", typeof (seg.distance || seg.data?.distance) === "number" ? `${(seg.distance || seg.data?.distance).toLocaleString("th-TH")} \u0E01\u0E21.` : seg.distance || seg.data?.distance), (seg.provider || seg.data?.provider || seg.company || seg.data?.company) && kv2("\u0E1A\u0E23\u0E34\u0E29\u0E31\u0E17", seg.provider || seg.data?.provider || seg.company || seg.data?.company), (seg.vehicle_type || seg.data?.vehicle_type || seg.car_type || seg.data?.car_type) && kv2("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E23\u0E16", seg.vehicle_type || seg.data?.vehicle_type || seg.car_type || seg.data?.car_type), (seg.seats || seg.data?.seats || seg.capacity || seg.data?.capacity) && kv2("\u0E08\u0E33\u0E19\u0E27\u0E19\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07", `${seg.seats || seg.data?.seats || seg.capacity || seg.data?.capacity} \u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07`), segmentPrice && /* @__PURE__ */ import_react12.default.createElement("div", { style: {
        marginTop: "8px",
        padding: "10px",
        background: "rgba(74, 222, 128, 0.15)",
        borderRadius: "6px",
        border: "1px solid rgba(74, 222, 128, 0.3)"
      } }, /* @__PURE__ */ import_react12.default.createElement("div", { style: { fontWeight: "700", fontSize: "16px", color: "#4ade80" } }, "\u{1F4B0} \u0E23\u0E32\u0E04\u0E32: ", moneyThb2(segmentPrice, segmentCurrency)), (seg.price_per_day || seg.data?.price_per_day) && /* @__PURE__ */ import_react12.default.createElement("div", { style: { fontSize: "13px", opacity: 0.9, marginTop: "4px" } }, "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E48\u0E2D\u0E27\u0E31\u0E19: ", moneyThb2(seg.price_per_day || seg.data?.price_per_day, segmentCurrency))), (seg.features || seg.data?.features || seg.amenities || seg.data?.amenities) && /* @__PURE__ */ import_react12.default.createElement("div", { style: { marginTop: "8px", fontSize: "13px" } }, /* @__PURE__ */ import_react12.default.createElement("div", { style: { fontWeight: "600", marginBottom: "4px" } }, "\u0E04\u0E38\u0E13\u0E2A\u0E21\u0E1A\u0E31\u0E15\u0E34:"), Array.isArray(seg.features || seg.data?.features || seg.amenities || seg.data?.amenities) ? (seg.features || seg.data?.features || seg.amenities || seg.data?.amenities).map((feature, fIdx) => /* @__PURE__ */ import_react12.default.createElement("div", { key: fIdx, style: { marginLeft: "8px" } }, "\u2713 ", feature)) : /* @__PURE__ */ import_react12.default.createElement("div", { style: { marginLeft: "8px" } }, seg.features || seg.data?.features || seg.amenities || seg.data?.amenities)), (seg.note || seg.data?.note || seg.description || seg.data?.description) && /* @__PURE__ */ import_react12.default.createElement("div", { style: {
        marginTop: "8px",
        padding: "8px",
        background: "rgba(255, 193, 7, 0.1)",
        borderRadius: "6px",
        fontSize: "13px"
      } }, /* @__PURE__ */ import_react12.default.createElement("span", { style: { fontWeight: "600" } }, "\u{1F4DD} \u0E2B\u0E21\u0E32\u0E22\u0E40\u0E2B\u0E15\u0E38: "), seg.note || seg.data?.note || seg.description || seg.data?.description));
    }), transportSegments.length > 1 && (() => {
      const totalPrice = transportSegments.reduce((sum, seg) => {
        const price = getPrice(seg);
        return sum + (price || 0);
      }, 0);
      if (totalPrice > 0) {
        return /* @__PURE__ */ import_react12.default.createElement("div", { style: {
          marginTop: "12px",
          padding: "12px",
          background: "rgba(74, 222, 128, 0.2)",
          borderRadius: "8px",
          border: "1px solid rgba(74, 222, 128, 0.4)",
          textAlign: "center"
        } }, /* @__PURE__ */ import_react12.default.createElement("div", { style: { fontWeight: "700", fontSize: "18px", color: "#4ade80" } }, "\u{1F4B0} \u0E23\u0E32\u0E04\u0E32\u0E23\u0E27\u0E21: ", moneyThb2(totalPrice, currency)));
      }
      return null;
    })()) : /* @__PURE__ */ import_react12.default.createElement(import_react12.default.Fragment, null, transport.type && kv2("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17", transport.type === "car_rental" ? "\u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32" : transport.type === "bus" ? "\u0E23\u0E16\u0E42\u0E14\u0E22\u0E2A\u0E32\u0E23" : transport.type === "train" ? "\u0E23\u0E16\u0E44\u0E1F" : transport.type === "metro" ? "\u0E23\u0E16\u0E44\u0E1F\u0E1F\u0E49\u0E32" : transport.type === "ferry" ? "\u0E40\u0E23\u0E37\u0E2D" : transport.type === "transfer" ? "\u0E23\u0E16\u0E23\u0E31\u0E1A\u0E2A\u0E48\u0E07" : transport.type), transport.route && kv2("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", transport.route), (transport.from || transport.origin || transport.data?.from || transport.data?.origin) && (transport.to || transport.destination || transport.data?.to || transport.data?.destination) && !transport.route && kv2("\u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07", `${transport.from || transport.origin || transport.data?.from || transport.data?.origin} \u2192 ${transport.to || transport.destination || transport.data?.to || transport.data?.destination}`), (transport.duration || transport.data?.duration) && kv2("\u0E23\u0E30\u0E22\u0E30\u0E40\u0E27\u0E25\u0E32", formatDuration4(transport.duration || transport.data?.duration)), (transport.distance || transport.data?.distance) && kv2("\u0E23\u0E30\u0E22\u0E30\u0E17\u0E32\u0E07", typeof (transport.distance || transport.data?.distance) === "number" ? `${(transport.distance || transport.data?.distance).toLocaleString("th-TH")} \u0E01\u0E21.` : transport.distance || transport.data?.distance), (transport.provider || transport.data?.provider || transport.company || transport.data?.company) && kv2("\u0E1A\u0E23\u0E34\u0E29\u0E31\u0E17", transport.provider || transport.data?.provider || transport.company || transport.data?.company), (transport.vehicle_type || transport.data?.vehicle_type || transport.car_type || transport.data?.car_type) && kv2("\u0E1B\u0E23\u0E30\u0E40\u0E20\u0E17\u0E23\u0E16", transport.vehicle_type || transport.data?.vehicle_type || transport.car_type || transport.data?.car_type), (transport.seats || transport.data?.seats || transport.capacity || transport.data?.capacity) && kv2("\u0E08\u0E33\u0E19\u0E27\u0E19\u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07", `${transport.seats || transport.data?.seats || transport.capacity || transport.data?.capacity} \u0E17\u0E35\u0E48\u0E19\u0E31\u0E48\u0E07`), (() => {
      const transportPrice = getPrice(transport);
      if (transportPrice) {
        return /* @__PURE__ */ import_react12.default.createElement("div", { style: {
          marginTop: "12px",
          padding: "12px",
          background: "rgba(74, 222, 128, 0.15)",
          borderRadius: "8px",
          border: "1px solid rgba(74, 222, 128, 0.3)"
        } }, /* @__PURE__ */ import_react12.default.createElement("div", { style: { fontWeight: "700", fontSize: "18px", color: "#4ade80", marginBottom: "4px" } }, "\u{1F4B0} \u0E23\u0E32\u0E04\u0E32: ", moneyThb2(transportPrice, currency)), (transport.price_per_day || transport.data?.price_per_day) && /* @__PURE__ */ import_react12.default.createElement("div", { style: { fontSize: "14px", opacity: 0.9, marginTop: "4px" } }, "\u0E23\u0E32\u0E04\u0E32\u0E15\u0E48\u0E2D\u0E27\u0E31\u0E19: ", moneyThb2(transport.price_per_day || transport.data?.price_per_day, currency)));
      }
      return null;
    })(), (transport.features || transport.data?.features || transport.amenities || transport.data?.amenities) && /* @__PURE__ */ import_react12.default.createElement("div", { style: { marginTop: "12px", padding: "10px", background: "rgba(255, 255, 255, 0.05)", borderRadius: "6px" } }, /* @__PURE__ */ import_react12.default.createElement("div", { style: { fontWeight: "600", marginBottom: "6px", fontSize: "14px" } }, "\u0E04\u0E38\u0E13\u0E2A\u0E21\u0E1A\u0E31\u0E15\u0E34:"), Array.isArray(transport.features || transport.data?.features || transport.amenities || transport.data?.amenities) ? (transport.features || transport.data?.features || transport.amenities || transport.data?.amenities).map((feature, idx) => /* @__PURE__ */ import_react12.default.createElement("div", { key: idx, style: { marginLeft: "8px", marginBottom: "4px" } }, "\u2713 ", feature)) : /* @__PURE__ */ import_react12.default.createElement("div", { style: { marginLeft: "8px" } }, transport.features || transport.data?.features || transport.amenities || transport.data?.amenities)), (transport.note || transport.data?.note || transport.description || transport.data?.description) && /* @__PURE__ */ import_react12.default.createElement("div", { style: {
      marginTop: "12px",
      padding: "10px",
      background: "rgba(255, 193, 7, 0.15)",
      borderRadius: "6px",
      fontSize: "14px"
    } }, /* @__PURE__ */ import_react12.default.createElement("span", { style: { fontWeight: "600" } }, "\u{1F4DD} \u0E2B\u0E21\u0E32\u0E22\u0E40\u0E2B\u0E15\u0E38: "), transport.note || transport.data?.note || transport.description || transport.data?.description)), /* @__PURE__ */ import_react12.default.createElement("div", { className: "slot-card-edit-hint", style: { marginTop: "12px" } }, '\u{1F4A1} \u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E43\u0E19\u0E41\u0E0A\u0E17\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E41\u0E01\u0E49\u0E44\u0E02 \u0E40\u0E0A\u0E48\u0E19 "\u0E02\u0E2D\u0E23\u0E16\u0E40\u0E0A\u0E48\u0E32" \u0E2B\u0E23\u0E37\u0E2D "\u0E40\u0E1B\u0E25\u0E35\u0E48\u0E22\u0E19\u0E40\u0E1B\u0E47\u0E19\u0E23\u0E16\u0E44\u0E1F"')));
  }

  // src/utils/textCorrection.js
  function detectLanguage(text) {
    if (!text || text.trim().length === 0) {
      return "unknown";
    }
    const thaiCharCount = (text.match(/[\u0E00-\u0E7F]/g) || []).length;
    const englishCharCount = (text.match(/[a-zA-Z]/g) || []).length;
    const totalChars = text.replace(/\s/g, "").length;
    if (totalChars === 0) {
      return "unknown";
    }
    const thaiRatio = thaiCharCount / totalChars;
    const englishRatio = englishCharCount / totalChars;
    if (thaiRatio > 0.3) {
      return "thai";
    } else if (englishRatio > 0.5) {
      return "english";
    } else if (thaiCharCount > englishCharCount) {
      return "thai";
    } else if (englishCharCount > thaiCharCount) {
      return "english";
    }
    return "mixed";
  }
  function levenshteinDistance(str1, str2) {
    const m = str1.length;
    const n = str2.length;
    const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));
    for (let i = 0; i <= m; i++) {
      dp[i][0] = i;
    }
    for (let j = 0; j <= n; j++) {
      dp[0][j] = j;
    }
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (str1[i - 1] === str2[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1];
        } else {
          dp[i][j] = Math.min(
            dp[i - 1][j] + 1,
            // deletion
            dp[i][j - 1] + 1,
            // insertion
            dp[i - 1][j - 1] + 1
            // substitution
          );
        }
      }
    }
    return dp[m][n];
  }
  function findClosestMatch(word, dictionary, maxDistance = 2) {
    let bestMatch = null;
    let minDistance = Infinity;
    for (const dictWord of dictionary) {
      const distance = levenshteinDistance(word.toLowerCase(), dictWord.toLowerCase());
      if (distance < minDistance && distance <= maxDistance) {
        minDistance = distance;
        bestMatch = dictWord;
      }
    }
    return minDistance <= maxDistance ? bestMatch : null;
  }
  var THAI_TRAVEL_WORDS = [
    "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27",
    "\u0E17\u0E23\u0E34\u0E1B",
    "\u0E1E\u0E31\u0E01",
    "\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21",
    "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19",
    "\u0E23\u0E32\u0E04\u0E32",
    "\u0E27\u0E31\u0E19\u0E17\u0E35\u0E48",
    "\u0E40\u0E27\u0E25\u0E32",
    "\u0E04\u0E19",
    "\u0E27\u0E31\u0E19",
    "\u0E04\u0E37\u0E19",
    "\u0E44\u0E1B",
    "\u0E01\u0E25\u0E31\u0E1A",
    "\u0E08\u0E32\u0E01",
    "\u0E16\u0E36\u0E07",
    "\u0E08\u0E2D\u0E07",
    "\u0E08\u0E2D\u0E07\u0E42\u0E23\u0E07\u0E41\u0E23\u0E21",
    "\u0E08\u0E2D\u0E07\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19",
    "\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01",
    "\u0E23\u0E35\u0E2A\u0E2D\u0E23\u0E4C\u0E17",
    "\u0E1A\u0E34\u0E19",
    "\u0E2A\u0E19\u0E32\u0E21\u0E1A\u0E34\u0E19",
    "\u0E15\u0E31\u0E4B\u0E27",
    "\u0E41\u0E1E\u0E47\u0E04\u0E40\u0E01\u0E08",
    "\u0E17\u0E31\u0E27\u0E23\u0E4C",
    "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27",
    "\u0E1E\u0E31\u0E01\u0E1C\u0E48\u0E2D\u0E19",
    "\u0E17\u0E30\u0E40\u0E25",
    "\u0E20\u0E39\u0E40\u0E02\u0E32",
    "\u0E15\u0E48\u0E32\u0E07\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28",
    "\u0E43\u0E19\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28",
    "\u0E01\u0E23\u0E38\u0E07\u0E40\u0E17\u0E1E",
    "\u0E40\u0E0A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48",
    "\u0E20\u0E39\u0E40\u0E01\u0E47\u0E15",
    "\u0E1E\u0E31\u0E17\u0E22\u0E32",
    "\u0E40\u0E01\u0E32\u0E30",
    "\u0E2B\u0E32\u0E14",
    "\u0E19\u0E49\u0E33\u0E15\u0E01"
  ];
  var ENGLISH_TRAVEL_WORDS = [
    "hotel",
    "flight",
    "travel",
    "trip",
    "booking",
    "price",
    "date",
    "time",
    "people",
    "days",
    "nights",
    "from",
    "to",
    "book",
    "reserve",
    "accommodation",
    "resort",
    "airport",
    "ticket",
    "package",
    "tour",
    "vacation",
    "beach",
    "mountain",
    "international",
    "domestic",
    "bangkok",
    "chiangmai",
    "phuket",
    "pattaya",
    "island",
    "waterfall",
    "want",
    "need",
    "help",
    "find",
    "recommend",
    "see",
    "choose",
    "buy",
    "airline",
    "airplane",
    "plane",
    "checkin",
    "checkout",
    "room",
    "swimming",
    "pool",
    "breakfast",
    "lunch",
    "dinner",
    "buffet",
    "wifi",
    "internet",
    "car",
    "rental",
    "taxi",
    "bus",
    "train",
    "boat",
    "ferry",
    "adult",
    "child",
    "baby",
    "bed",
    "single",
    "double",
    "twin",
    "morning",
    "afternoon",
    "evening",
    "night",
    "midnight",
    "cheap",
    "expensive",
    "discount",
    "promotion",
    "coupon",
    "confirm",
    "cancel",
    "change",
    "edit",
    "thailand",
    "japan",
    "korea",
    "china",
    "singapore",
    "malaysia",
    "vietnam",
    "cambodia",
    "laos",
    "myanmar",
    "india",
    "nepal",
    "england",
    "france",
    "italy",
    "spain",
    "germany",
    "switzerland",
    "australia",
    "newzealand",
    "america",
    "canada",
    "mexico"
  ];
  function correctTypos(text) {
    if (!text || text.trim().length === 0) {
      return { corrected: text, suggestions: [] };
    }
    const language = detectLanguage(text);
    const words = text.split(/\s+/);
    const corrections = [];
    const suggestions = [];
    const correctedWords = words.map((word, index) => {
      if (word.length < 2 || /^[0-9\s\-.,!?]+$/.test(word)) {
        return word;
      }
      let corrected = word;
      let suggestion = null;
      if (language === "thai" || language === "mixed") {
        const thaiMatch = findClosestMatch(word, THAI_TRAVEL_WORDS, 2);
        if (thaiMatch && thaiMatch !== word) {
          corrected = thaiMatch;
          suggestion = thaiMatch;
          corrections.push({ original: word, corrected: thaiMatch, index });
        }
      }
      if (language === "english" || language === "mixed") {
        const englishMatch = findClosestMatch(word, ENGLISH_TRAVEL_WORDS, 2);
        if (englishMatch && englishMatch !== word) {
          corrected = englishMatch;
          suggestion = englishMatch;
          corrections.push({ original: word, corrected: englishMatch, index });
        }
      }
      return corrected;
    });
    const correctedText = correctedWords.join(" ");
    return {
      corrected: correctedText,
      original: text,
      corrections,
      language,
      hasCorrections: corrections.length > 0
    };
  }
  function detectLanguageMismatch(text, expectedLanguage = null) {
    const detected = detectLanguage(text);
    if (expectedLanguage && detected !== expectedLanguage && detected !== "mixed") {
      return {
        detected,
        expected: expectedLanguage,
        mismatch: true,
        suggestion: `\u0E04\u0E38\u0E13\u0E01\u0E33\u0E25\u0E31\u0E07\u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E40\u0E1B\u0E47\u0E19${detected === "english" ? "\u0E20\u0E32\u0E29\u0E32\u0E2D\u0E31\u0E07\u0E01\u0E24\u0E29" : "\u0E20\u0E32\u0E29\u0E32\u0E44\u0E17\u0E22"} \u0E41\u0E15\u0E48\u0E23\u0E30\u0E1A\u0E1A\u0E04\u0E32\u0E14\u0E2B\u0E27\u0E31\u0E07${expectedLanguage === "english" ? "\u0E20\u0E32\u0E29\u0E32\u0E2D\u0E31\u0E07\u0E01\u0E24\u0E29" : "\u0E20\u0E32\u0E29\u0E32\u0E44\u0E17\u0E22"}`
      };
    }
    return {
      detected,
      expected: expectedLanguage,
      mismatch: false
    };
  }

  // src/pages/chat/AITravelChat.jsx
  var import_meta = {};
  var ChatErrorBoundary = class extends import_react13.default.Component {
    constructor(props) {
      super(props);
      this.state = { hasError: false, error: null, errorInfo: null };
    }
    static getDerivedStateFromError(error) {
      return { hasError: true };
    }
    componentDidCatch(error, errorInfo) {
      console.error("Chat Error Boundary caught an error:", error, errorInfo);
      sendTelemetry({ location: "AITravelChat.jsx:ChatErrorBoundary.componentDidCatch", message: "ErrorBoundary caught error", data: { errorMessage: String(error?.message), errorName: error?.name, componentStack: (errorInfo?.componentStack || "").slice(0, 500) }, timestamp: Date.now(), runId: "run1", hypothesisId: "H1" });
      this.setState({
        error,
        errorInfo
      });
    }
    render() {
      if (this.state.hasError) {
        return /* @__PURE__ */ import_react13.default.createElement("div", { style: {
          padding: "2rem",
          textAlign: "center",
          color: "#fff",
          background: "rgba(220, 38, 38, 0.1)",
          borderRadius: "8px",
          margin: "1rem"
        } }, /* @__PURE__ */ import_react13.default.createElement("h3", { style: { color: "#ef4444", marginBottom: "1rem" } }, "\u26A0\uFE0F \u0E40\u0E01\u0E34\u0E14\u0E02\u0E49\u0E2D\u0E1C\u0E34\u0E14\u0E1E\u0E25\u0E32\u0E14\u0E43\u0E19\u0E01\u0E32\u0E23\u0E41\u0E2A\u0E14\u0E07\u0E1C\u0E25"), /* @__PURE__ */ import_react13.default.createElement("p", { style: { marginBottom: "1rem", opacity: 0.8 } }, "\u0E40\u0E01\u0E34\u0E14\u0E02\u0E49\u0E2D\u0E1C\u0E34\u0E14\u0E1E\u0E25\u0E32\u0E14\u0E17\u0E35\u0E48\u0E44\u0E21\u0E48\u0E04\u0E32\u0E14\u0E04\u0E34\u0E14 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E23\u0E35\u0E40\u0E1F\u0E23\u0E0A\u0E2B\u0E19\u0E49\u0E32\u0E2B\u0E23\u0E37\u0E2D\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07"), /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            onClick: () => {
              this.setState({ hasError: false, error: null, errorInfo: null });
              window.location.reload();
            },
            style: {
              padding: "8px 16px",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "14px"
            }
          },
          "\u{1F504} \u0E23\u0E35\u0E40\u0E1F\u0E23\u0E0A\u0E2B\u0E19\u0E49\u0E32"
        ), this.state.error && /* @__PURE__ */ import_react13.default.createElement("details", { style: { marginTop: "1rem", textAlign: "left", fontSize: "12px", opacity: 0.7 } }, /* @__PURE__ */ import_react13.default.createElement("summary", { style: { cursor: "pointer", marginBottom: "0.5rem" } }, "\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E02\u0E49\u0E2D\u0E1C\u0E34\u0E14\u0E1E\u0E25\u0E32\u0E14 (Development)"), /* @__PURE__ */ import_react13.default.createElement("pre", { style: { background: "rgba(0,0,0,0.3)", padding: "1rem", borderRadius: "4px", overflow: "auto" } }, this.state.error.toString(), this.state.errorInfo?.componentStack)));
      }
      return this.props.children;
    }
  };
  var API_BASE_URL = import_meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  var LS_TRIPS_KEY = "ai_travel_trips_v1";
  var LS_ACTIVE_TRIP_KEY = "ai_travel_active_trip_id_v1";
  function nowISO() {
    return (/* @__PURE__ */ new Date()).toISOString();
  }
  var GREETINGS = [
    "\u0E2A\u0E27\u0E31\u0E2A\u0E14\u0E35\u0E04\u0E48\u0E30\u0E04\u0E38\u0E13 {name} \u0E14\u0E34\u0E09\u0E31\u0E19\u0E04\u0E37\u0E2D AI Travel Agent \u{1F499} \u0E40\u0E25\u0E48\u0E32\u0E44\u0E2D\u0E40\u0E14\u0E35\u0E22\u0E17\u0E23\u0E34\u0E1B\u0E02\u0E2D\u0E07\u0E04\u0E38\u0E13\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22",
    "\u0E22\u0E34\u0E19\u0E14\u0E35\u0E15\u0E49\u0E2D\u0E19\u0E23\u0E31\u0E1A\u0E04\u0E48\u0E30\u0E04\u0E38\u0E13 {name} \u2708\uFE0F \u0E27\u0E31\u0E19\u0E19\u0E35\u0E49\u0E2D\u0E22\u0E32\u0E01\u0E43\u0E2B\u0E49\u0E14\u0E34\u0E09\u0E31\u0E19\u0E0A\u0E48\u0E27\u0E22\u0E41\u0E1E\u0E25\u0E19\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E19\u0E1D\u0E31\u0E19\u0E17\u0E35\u0E48\u0E44\u0E2B\u0E19\u0E14\u0E35\u0E04\u0E30? \u0E1A\u0E2D\u0E01\u0E21\u0E32\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22\u0E04\u0E48\u0E30!",
    "\u0E2A\u0E27\u0E31\u0E2A\u0E14\u0E35\u0E04\u0E48\u0E30\u0E04\u0E38\u0E13 {name}! \u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E08\u0E30\u0E2D\u0E2D\u0E01\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E2B\u0E23\u0E37\u0E2D\u0E22\u0E31\u0E07\u0E04\u0E30? \u{1F30D} \u0E08\u0E30\u0E44\u0E1B\u0E17\u0E30\u0E40\u0E25 \u0E20\u0E39\u0E40\u0E02\u0E32 \u0E2B\u0E23\u0E37\u0E2D\u0E15\u0E48\u0E32\u0E07\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28 \u0E43\u0E2B\u0E49\u0E14\u0E34\u0E09\u0E31\u0E19\u0E0A\u0E48\u0E27\u0E22\u0E08\u0E31\u0E14\u0E01\u0E32\u0E23\u0E43\u0E2B\u0E49\u0E19\u0E30\u0E04\u0E30",
    "\u0E2A\u0E27\u0E31\u0E2A\u0E14\u0E35\u0E04\u0E48\u0E30\u0E04\u0E38\u0E13 {name} \u{1F499} \u0E27\u0E31\u0E19\u0E19\u0E35\u0E49\u0E21\u0E35\u0E41\u0E1E\u0E25\u0E19\u0E08\u0E30\u0E44\u0E1B\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E17\u0E35\u0E48\u0E44\u0E2B\u0E19\u0E43\u0E19\u0E43\u0E08\u0E2B\u0E23\u0E37\u0E2D\u0E22\u0E31\u0E07\u0E04\u0E30? \u0E43\u0E2B\u0E49\u0E14\u0E34\u0E09\u0E31\u0E19\u0E0A\u0E48\u0E27\u0E22\u0E2B\u0E32\u0E44\u0E1F\u0E25\u0E15\u0E4C\u0E2B\u0E23\u0E37\u0E2D\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01\u0E14\u0E35\u0E46 \u0E43\u0E2B\u0E49\u0E44\u0E2B\u0E21\u0E04\u0E30?",
    "\u0E22\u0E34\u0E19\u0E14\u0E35\u0E17\u0E35\u0E48\u0E44\u0E14\u0E49\u0E1E\u0E1A\u0E01\u0E31\u0E19\u0E04\u0E48\u0E30\u0E04\u0E38\u0E13 {name} \u2728 \u0E27\u0E31\u0E19\u0E19\u0E35\u0E49\u0E2D\u0E22\u0E32\u0E01\u0E44\u0E1B\u0E1E\u0E31\u0E01\u0E1C\u0E48\u0E2D\u0E19\u0E41\u0E1A\u0E1A\u0E44\u0E2B\u0E19\u0E14\u0E35\u0E04\u0E30? \u0E40\u0E25\u0E48\u0E32\u0E04\u0E27\u0E32\u0E21\u0E15\u0E49\u0E2D\u0E07\u0E01\u0E32\u0E23\u0E02\u0E2D\u0E07\u0E04\u0E38\u0E13\u0E43\u0E2B\u0E49\u0E14\u0E34\u0E09\u0E31\u0E19\u0E1F\u0E31\u0E07\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22\u0E04\u0E48\u0E30"
  ];
  function shortDate(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" });
    } catch {
      return iso || "";
    }
  }
  var VISA_FREE_WHITELIST_BY_NATIONALITY = {
    TH: ["JP", "KR", "SG", "MY", "VN", "LA", "KH", "ID", "PH", "HK", "MO", "TW"]
  };
  var DESTINATION_COUNTRY_KEYWORDS = {
    JP: ["japan", "\u0E0D\u0E35\u0E48\u0E1B\u0E38\u0E48\u0E19", "tokyo", "\u0E42\u0E15\u0E40\u0E01\u0E35\u0E22\u0E27", "osaka", "\u0E42\u0E2D\u0E0B\u0E32\u0E01\u0E49\u0E32", "nrt", "hnd", "kix"],
    KR: ["korea", "\u0E40\u0E01\u0E32\u0E2B\u0E25\u0E35", "seoul", "\u0E42\u0E0B\u0E25", "icn", "busan", "\u0E1B\u0E39\u0E0B\u0E32\u0E19"],
    SG: ["singapore", "\u0E2A\u0E34\u0E07\u0E04\u0E42\u0E1B\u0E23\u0E4C", "sin", "changi"],
    MY: ["malaysia", "\u0E21\u0E32\u0E40\u0E25\u0E40\u0E0B\u0E35\u0E22", "kuala lumpur", "kul", "penang", "\u0E1B\u0E35\u0E19\u0E31\u0E07"],
    VN: ["vietnam", "\u0E40\u0E27\u0E35\u0E22\u0E14\u0E19\u0E32\u0E21", "hanoi", "\u0E2E\u0E32\u0E19\u0E2D\u0E22", "ho chi minh", "\u0E42\u0E2E\u0E08\u0E34\u0E21\u0E34\u0E19\u0E2B\u0E4C", "sgn", "han"],
    LA: ["laos", "\u0E25\u0E32\u0E27", "vientiane", "\u0E40\u0E27\u0E35\u0E22\u0E07\u0E08\u0E31\u0E19\u0E17\u0E19\u0E4C", "vte", "luang prabang", "lpq"],
    KH: ["cambodia", "\u0E01\u0E31\u0E21\u0E1E\u0E39\u0E0A\u0E32", "phnom penh", "\u0E1E\u0E19\u0E21\u0E40\u0E1B\u0E0D", "pnh", "siem reap", "rep"],
    ID: ["indonesia", "\u0E2D\u0E34\u0E19\u0E42\u0E14\u0E19\u0E35\u0E40\u0E0B\u0E35\u0E22", "jakarta", "\u0E08\u0E32\u0E01\u0E32\u0E23\u0E4C\u0E15\u0E32", "bali", "\u0E1A\u0E32\u0E2B\u0E25\u0E35", "cgk", "dps"],
    PH: ["philippines", "\u0E1F\u0E34\u0E25\u0E34\u0E1B\u0E1B\u0E34\u0E19\u0E2A\u0E4C", "manila", "\u0E21\u0E30\u0E19\u0E34\u0E25\u0E32", "mnl", "cebu", "\u0E40\u0E0B\u0E1A\u0E39"],
    HK: ["hong kong", "\u0E2E\u0E48\u0E2D\u0E07\u0E01\u0E07", "hkg"],
    MO: ["macau", "\u0E21\u0E32\u0E40\u0E01\u0E4A\u0E32", "mfm"],
    TW: ["taiwan", "\u0E44\u0E15\u0E49\u0E2B\u0E27\u0E31\u0E19", "taipei", "\u0E44\u0E17\u0E40\u0E1B", "tpe", "kaohsiung", "\u0E40\u0E01\u0E32\u0E2A\u0E07"]
  };
  function normalizeNationalityCode(nationality) {
    if (!nationality || typeof nationality !== "string") return "";
    return nationality.trim().toUpperCase().slice(0, 2);
  }
  function resolveDestinationCountryCode(destinationText) {
    const text = (destinationText || "").toString().trim().toLowerCase();
    if (!text) return null;
    return Object.entries(DESTINATION_COUNTRY_KEYWORDS).find(
      ([, keywords]) => keywords.some((keyword) => text.includes(keyword))
    )?.[0] || null;
  }
  function isVisaFreeRoute(nationality, destinationText) {
    const nat = normalizeNationalityCode(nationality);
    const countryCode = resolveDestinationCountryCode(destinationText);
    if (!nat || !countryCode) return false;
    return (VISA_FREE_WHITELIST_BY_NATIONALITY[nat] || []).includes(countryCode);
  }
  var _msgSeq = 0;
  function makeId(prefix = "trip") {
    _msgSeq += 1;
    return `${prefix}_${Date.now()}_${_msgSeq}_${Math.random().toString(36).slice(2, 10)}`;
  }
  function sendTelemetry(data) {
    if (import_meta.env.VITE_TELEMETRY_ENABLED !== "true") return;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 50);
      fetch("http://127.0.0.1:7243/ingest/40f320da-1b3b-4d52-a48b-ec2dd1dbba89", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        signal: controller.signal,
        mode: "no-cors"
      }).then(() => clearTimeout(timeoutId)).catch(() => {
        clearTimeout(timeoutId);
      });
    } catch (e) {
    }
  }
  function defaultWelcomeMessage(userName = "\u0E04\u0E38\u0E13") {
    const randomGreeting = GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
    const personalizedGreeting = randomGreeting.replace("{name}", userName);
    return {
      id: 1,
      type: "bot",
      text: personalizedGreeting
    };
  }
  function createNewTrip(title = "\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48", userName = "\u0E04\u0E38\u0E13") {
    const tripId = makeId("trip");
    const chatId = makeId("chat");
    return {
      tripId,
      // ✅ trip_id: สำหรับ 1 ทริป (1 trip = หลาย chat ได้)
      chatId,
      // ✅ chat_id: สำหรับแต่ละแชท (1 chat = 1 chat_id)
      title,
      createdAt: nowISO(),
      updatedAt: nowISO(),
      messages: [defaultWelcomeMessage(userName)],
      pinned: false
      // เพิ่ม field สำหรับปักหมุด
    };
  }
  function AITravelChat({ user, onLogout, onSignIn, initialPrompt = "", onNavigateToBookings, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, notificationCount = 0, notifications = [], onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, onRefreshNotifications = null, onMarkNotificationAsRead = null }) {
    const userId = user?.user_id || user?.id || "demo_user";
    const [isLoadingSessions, setIsLoadingSessions] = (0, import_react13.useState)(false);
    (0, import_react13.useEffect)(() => {
      if (!user?.id) return;
      let cancelled = false;
      setIsLoadingSessions(true);
      const headers = {
        "Content-Type": "application/json",
        "X-User-ID": user?.user_id || user?.id || ""
      };
      fetch(`${API_BASE_URL}/api/chat/sessions`, { headers, credentials: "include" }).then((res) => res.json()).then((data) => {
        if (cancelled) return;
        const list = data.sessions || [];
        if (data.require_login) {
          setTrips([]);
          setIsLoadingSessions(false);
          return;
        }
        const nextTrips = list.map((s) => ({
          tripId: s.trip_id || s.chat_id,
          chatId: s.chat_id || s.session_id && s.session_id.split("::")[1] || s.session_id,
          title: s.title || "\u0E01\u0E32\u0E23\u0E2A\u0E19\u0E17\u0E19\u0E32\u0E43\u0E2B\u0E21\u0E48",
          updatedAt: s.last_updated || s.created_at,
          messages: [],
          userId: user.id,
          pinned: false
        })).filter((t2) => t2.chatId);
        if (nextTrips.length > 0) {
          setTrips(nextTrips);
          localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(nextTrips));
        } else {
          const displayName = user?.first_name || user?.name || "\u0E04\u0E38\u0E13";
          const newTrip = createNewTrip("\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48", displayName);
          newTrip.userId = user.id;
          setTrips([newTrip]);
          localStorage.setItem(LS_TRIPS_KEY, JSON.stringify([newTrip]));
        }
      }).catch((err) => {
        if (!cancelled) console.error("Fetch sessions error:", err);
      }).finally(() => {
        if (!cancelled) setIsLoadingSessions(false);
      });
      return () => {
        cancelled = true;
      };
    }, [user?.id]);
    const [userTrips, setUserTrips] = (0, import_react13.useState)([]);
    const [isLoadingUserTrips, setIsLoadingUserTrips] = (0, import_react13.useState)(false);
    const [tripSelectorOpen, setTripSelectorOpen] = (0, import_react13.useState)(false);
    const tripSelectorRef = (0, import_react13.useRef)(null);
    const fetchUserTrips = async () => {
      if (!user?.id) return;
      setIsLoadingUserTrips(true);
      try {
        const res = await fetch(`${API_BASE_URL}/api/trips`, {
          credentials: "include",
          headers: { "X-User-ID": user?.user_id || user?.id || "" }
        });
        if (res.ok) {
          const data = await res.json();
          setUserTrips(data.trips || []);
        }
      } catch (err) {
        console.error("fetchUserTrips error:", err);
      } finally {
        setIsLoadingUserTrips(false);
      }
    };
    (0, import_react13.useEffect)(() => {
      fetchUserTrips();
    }, [user?.id]);
    (0, import_react13.useEffect)(() => {
      const handler = (e) => {
        if (tripSelectorRef.current && !tripSelectorRef.current.contains(e.target)) {
          setTripSelectorOpen(false);
        }
      };
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }, []);
    const ensureTripRegistered = async (tripId, title) => {
      if (!tripId || !user?.id) return;
      try {
        await fetch(`${API_BASE_URL}/api/trips`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": user?.user_id || user?.id || ""
          },
          body: JSON.stringify({ trip_id: tripId, title: title || "\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48" })
        });
      } catch (err) {
        console.warn("ensureTripRegistered failed (non-fatal):", err);
      }
    };
    const linkChatToTrip = async (tripId) => {
      const currentChat = trips.find((t2) => (t2.chatId || t2.tripId) === activeTripId);
      if (!currentChat || !tripId) return;
      const chatId = currentChat.chatId || currentChat.tripId;
      try {
        const res = await fetch(`${API_BASE_URL}/api/trips/${tripId}/link-chat`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": user?.user_id || user?.id || ""
          },
          body: JSON.stringify({ chat_id: chatId })
        });
        if (res.ok) {
          setTrips((prev) => prev.map(
            (t2) => (t2.chatId || t2.tripId) === activeTripId ? { ...t2, tripId } : t2
          ));
          await fetchUserTrips();
          console.log(`\u2705 Linked chat ${chatId} to trip ${tripId}`);
        }
      } catch (err) {
        console.error("linkChatToTrip error:", err);
      }
      setTripSelectorOpen(false);
    };
    const handleCreateAndLinkTrip = async () => {
      if (!user?.id) return;
      try {
        const res = await fetch(`${API_BASE_URL}/api/trips`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": user?.user_id || user?.id || ""
          },
          body: JSON.stringify({ title: "\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48" })
        });
        if (res.ok) {
          const newTrip = await res.json();
          await linkChatToTrip(newTrip.trip_id);
          await fetchUserTrips();
        }
      } catch (err) {
        console.error("handleCreateAndLinkTrip error:", err);
      }
    };
    const [activeTab, setActiveTab] = (0, import_react13.useState)("flights");
    const REFRESH_COOLDOWN_MS = 4e3;
    const lastRefreshAtRef = (0, import_react13.useRef)({});
    const messagesEndRef = (0, import_react13.useRef)(null);
    const inputRef = (0, import_react13.useRef)(null);
    const [trips, setTrips] = (0, import_react13.useState)(() => {
      const displayName = user?.first_name || user?.name || "\u0E04\u0E38\u0E13";
      const currentUserId = user?.id || userId;
      try {
        const raw = localStorage.getItem(LS_TRIPS_KEY);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed) && parsed.length > 0) {
            const userTrips2 = parsed.filter((trip) => {
              const tripUserId = trip.userId || trip.user_id;
              if (tripUserId && tripUserId !== currentUserId) {
                console.warn(`\u26A0\uFE0F Filtered out trip from different user: ${trip.tripId} (user: ${tripUserId}, current: ${currentUserId})`);
                return false;
              }
              return true;
            });
            if (userTrips2.length > 0) {
              const migrated = userTrips2.map((trip) => {
                if (!trip.chatId) {
                  trip.chatId = trip.tripId || makeId("chat");
                  console.log(`\u{1F504} Migrated trip to add chatId: ${trip.tripId} \u2192 ${trip.chatId}`);
                }
                if (!trip.userId && !trip.user_id) {
                  trip.userId = currentUserId;
                }
                return trip;
              });
              console.log(`\u2705 Loaded ${migrated.length} trips for user: ${currentUserId}`);
              return migrated;
            } else {
              console.log(`\u2139\uFE0F No trips found for user: ${currentUserId}, creating new trip`);
            }
          }
        }
      } catch (e) {
        console.error("\u274C Failed to load trips from localStorage:", e);
      }
      const newTrip = createNewTrip("\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48", displayName);
      newTrip.userId = currentUserId;
      return [newTrip];
    });
    (0, import_react13.useEffect)(() => {
      const currentUserId = user?.id || userId;
      const tripsUserId = trips[0]?.userId || trips[0]?.user_id;
      if (currentUserId && tripsUserId && tripsUserId !== currentUserId) {
        console.warn(`\u{1F6A8} SECURITY: User changed from ${tripsUserId} to ${currentUserId}, clearing trips`);
        setTrips(() => {
          const displayName = user?.first_name || user?.name || "\u0E04\u0E38\u0E13";
          const newTrip = createNewTrip("\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48", displayName);
          newTrip.userId = currentUserId;
          return [newTrip];
        });
        localStorage.removeItem(LS_TRIPS_KEY);
        localStorage.removeItem(LS_ACTIVE_TRIP_KEY);
        sessionStorage.removeItem("ai_travel_loaded_trips");
      }
    }, [user?.id, userId]);
    const [activeTripId, setActiveTripId] = (0, import_react13.useState)(() => {
      try {
        const saved = localStorage.getItem(LS_ACTIVE_TRIP_KEY);
        if (saved) {
          console.log(`\u2705 Restored activeTripId from localStorage: ${saved}`);
          return saved;
        }
      } catch (e) {
        console.warn("Failed to restore activeTripId from localStorage:", e);
      }
      return null;
    });
    const activeChat = (0, import_react13.useMemo)(() => {
      if (!activeTripId) return null;
      const currentUserId = user?.id || userId;
      const userTrips2 = trips.filter((t2) => {
        const tripUserId = t2.userId || t2.user_id;
        return !tripUserId || tripUserId === currentUserId;
      });
      let found = userTrips2.find((t2) => t2.chatId === activeTripId);
      if (found) return found;
      found = userTrips2.find((t2) => t2.tripId === activeTripId);
      if (found) return found;
      const tripsWithSameTripId = userTrips2.filter((t2) => t2.tripId === activeTripId);
      return tripsWithSameTripId.length > 0 ? tripsWithSameTripId[0] : null;
    }, [trips, activeTripId, user?.id, userId]);
    const isAdmin = Boolean(user?.is_admin) || user?.email === "admin@example.com";
    const [isLoadingHistory, setIsLoadingHistory] = (0, import_react13.useState)(false);
    const [isRefreshingHistory, setIsRefreshingHistory] = (0, import_react13.useState)(false);
    const isRefreshingRef = (0, import_react13.useRef)(false);
    const historyCache = (0, import_react13.useRef)(/* @__PURE__ */ new Map());
    const loadedTripsRef = (0, import_react13.useRef)(/* @__PURE__ */ new Set());
    const isFetchingHistoryRef = (0, import_react13.useRef)(false);
    const isToolCallText = (text) => {
      if (!text || typeof text !== "string") return false;
      const t2 = text.trim();
      if (!t2.startsWith("{")) return false;
      try {
        const obj = JSON.parse(t2);
        return obj && typeof obj === "object" && typeof obj.tool === "string";
      } catch {
        return false;
      }
    };
    const mapHistoryToMessages = (data) => {
      if (!data.history || data.history.length === 0) return null;
      return data.history.filter((m) => {
        if (m.role === "tool") return false;
        if (isToolCallText(m.text || m.content || "")) return false;
        return true;
      }).map((m, idx) => ({
        ...m,
        id: m.id || `restored_${idx}_${makeId("hist")}`,
        type: m.role === "assistant" ? "bot" : m.role || m.type,
        planChoices: m.planChoices || m.plan_choices || [],
        slotChoices: m.slotChoices || m.slot_choices || [],
        slotIntent: m.slotIntent || m.slot_intent || null,
        agentState: m.agentState || m.agent_state || null,
        travelSlots: m.travelSlots || m.travel_slots || null,
        currentPlan: m.currentPlan || m.current_plan || null,
        tripTitle: m.tripTitle || m.trip_title || null,
        searchResults: m.searchResults || m.search_results || {},
        suggestions: m.suggestions || [],
        cachedOptions: m.cachedOptions || m.cached_options || null,
        cacheValidation: m.cacheValidation || m.cache_validation || null,
        workflowValidation: m.workflowValidation || m.workflow_validation || null,
        reasoning: m.reasoning || null,
        memorySuggestions: m.memorySuggestions || m.memory_suggestions || null,
        debug: m.debug || null
      }));
    };
    const applyMessagesToTrip = (0, import_react13.useCallback)((chatId, messages2, setError = false) => {
      const findIdx = (list) => list.findIndex((t2) => t2.chatId === chatId || t2.tripId === chatId);
      setTrips((prev) => {
        const idx = findIdx(prev);
        if (idx === -1) return prev;
        const next = [...prev];
        next[idx] = { ...next[idx], messages: messages2 || [], _loadError: setError };
        return next;
      });
      if (messages2 && messages2.length > 0) {
        const latest = messages2.slice().reverse().find((m) => m.type === "bot" && (m.planChoices?.length || m.currentPlan || m.travelSlots));
        if (latest) {
          if (latest.planChoices?.length) setLatestPlanChoices(latest.planChoices);
          if (latest.currentPlan) setSelectedPlan(latest.currentPlan);
          if (latest.travelSlots) setSelectedTravelSlots(latest.travelSlots);
          setLatestBotMessage(latest);
        }
      }
    }, []);
    const loadHistoryForChat = (0, import_react13.useCallback)((chatIdToLoad) => {
      if (!chatIdToLoad) return;
      const cached = historyCache.current.get(chatIdToLoad);
      if (cached !== void 0) {
        loadedTripsRef.current.add(chatIdToLoad);
        if (cached && cached.length > 0) applyMessagesToTrip(chatIdToLoad, cached, false);
        return;
      }
      if (isFetchingHistoryRef.current) return;
      isFetchingHistoryRef.current = true;
      const findTripIndex = (list) => list.findIndex((t2) => t2.chatId === chatIdToLoad || t2.tripId === chatIdToLoad);
      isFetchingHistoryRef.current = true;
      (async () => {
        try {
          setIsLoadingHistory(true);
          const historyHeaders = {
            "Content-Type": "application/json",
            "X-Trip-ID": chatIdToLoad,
            "X-User-ID": user?.user_id || user?.id || ""
          };
          const res = await fetch(`${API_BASE_URL}/api/chat/history/${chatIdToLoad}`, {
            headers: historyHeaders,
            credentials: "include"
          });
          if (!res.ok) {
            historyCache.current.set(chatIdToLoad, []);
            loadedTripsRef.current.add(chatIdToLoad);
            setTrips((prev) => {
              const idx = findTripIndex(prev);
              if (idx === -1) return prev;
              const next = [...prev];
              next[idx] = { ...next[idx], messages: [], _loadError: true };
              return next;
            });
            return;
          }
          const data = await res.json();
          let restoredMessages;
          try {
            restoredMessages = mapHistoryToMessages(data);
          } catch (mapErr) {
            console.warn("Failed to map history (malformed data):", mapErr);
            restoredMessages = [];
          }
          loadedTripsRef.current.add(chatIdToLoad);
          const currentUserId = user?.id || userId;
          if (!restoredMessages || restoredMessages.length === 0) {
            historyCache.current.set(chatIdToLoad, []);
            setTrips((prev) => {
              const idx = findTripIndex(prev);
              if (idx === -1) return prev;
              const next = [...prev];
              next[idx] = { ...next[idx], messages: [], updatedAt: next[idx].updatedAt, userId: next[idx].userId || currentUserId, _loadError: false };
              return next;
            });
            return;
          }
          const seen = /* @__PURE__ */ new Set();
          const uniqueMessages = restoredMessages.filter((msg) => {
            const key = msg.id || `${msg.type}_${msg.text}_${msg.timestamp || ""}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
          historyCache.current.set(chatIdToLoad, uniqueMessages);
          setTrips((prev) => {
            const idx = findTripIndex(prev);
            if (idx === -1) return prev;
            const newTrips = [...prev];
            newTrips[idx] = { ...newTrips[idx], messages: uniqueMessages, updatedAt: nowISO(), userId: newTrips[idx].userId || currentUserId, _loadError: false };
            return newTrips;
          });
          const latestBotWithData = uniqueMessages.slice().reverse().find((m) => m.type === "bot" && (m.planChoices?.length || m.currentPlan || m.travelSlots));
          if (latestBotWithData) {
            if (latestBotWithData.planChoices?.length) setLatestPlanChoices(latestBotWithData.planChoices);
            if (latestBotWithData.currentPlan) setSelectedPlan(latestBotWithData.currentPlan);
            if (latestBotWithData.travelSlots) setSelectedTravelSlots(latestBotWithData.travelSlots);
            setLatestBotMessage(latestBotWithData);
          }
        } catch (err) {
          console.error("Fetch chat history error:", err);
          historyCache.current.set(chatIdToLoad, []);
          loadedTripsRef.current.add(chatIdToLoad);
          setTrips((prev) => {
            const idx = findTripIndex(prev);
            if (idx === -1) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], messages: [], _loadError: true };
            return next;
          });
        } finally {
          setIsLoadingHistory(false);
          isFetchingHistoryRef.current = false;
        }
      })();
    }, [user?.id, user?.user_id, userId, mapHistoryToMessages, applyMessagesToTrip]);
    (0, import_react13.useEffect)(() => {
      if (!activeTripId) return;
      setShowTripSummary(false);
      const chatId = activeChat?.chatId || activeTripId;
      const cached = historyCache.current.get(chatId);
      if (cached !== void 0) {
        loadedTripsRef.current.add(chatId);
        if (cached && cached.length > 0) {
          setTrips((prev) => {
            const idx = prev.findIndex((t2) => t2.chatId === chatId || t2.tripId === chatId);
            if (idx === -1) return prev;
            const existing = prev[idx].messages || [];
            if (existing.length >= cached.length) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], messages: cached, _loadError: false };
            return next;
          });
          const latestBotWithData = cached.slice().reverse().find((m) => m.type === "bot" && (m.planChoices?.length || m.currentPlan || m.travelSlots));
          if (latestBotWithData) {
            if (latestBotWithData.planChoices?.length) setLatestPlanChoices(latestBotWithData.planChoices);
            if (latestBotWithData.currentPlan) setSelectedPlan(latestBotWithData.currentPlan);
            if (latestBotWithData.travelSlots) setSelectedTravelSlots(latestBotWithData.travelSlots);
            setLatestBotMessage(latestBotWithData);
          }
        }
        return;
      }
      loadHistoryForChat(chatId);
    }, [activeTripId, activeChat?.chatId, loadHistoryForChat]);
    const [inputText, setInputText] = (0, import_react13.useState)("");
    const [processingTripId, setProcessingTripId] = (0, import_react13.useState)(null);
    const [showTripSummary, setShowTripSummary] = (0, import_react13.useState)(false);
    const isTyping = processingTripId !== null && activeChat && (processingTripId === activeTripId || processingTripId === activeChat.tripId || processingTripId === activeChat.chatId);
    const [isRecording, setIsRecording] = (0, import_react13.useState)(false);
    const [isVoiceMode, setIsVoiceMode] = (0, import_react13.useState)(false);
    const [voiceModeNotice, setVoiceModeNotice] = (0, import_react13.useState)("");
    const [voiceDraft, setVoiceDraft] = (0, import_react13.useState)("");
    const recognitionRef = (0, import_react13.useRef)(null);
    const synthesisRef = (0, import_react13.useRef)(null);
    const isVoiceModeRef = (0, import_react13.useRef)(false);
    const voiceAwaitingResponseRef = (0, import_react13.useRef)(false);
    const voiceAiSpeakingRef = (0, import_react13.useRef)(false);
    const isMountedRef = (0, import_react13.useRef)(true);
    (0, import_react13.useEffect)(() => {
      return () => {
        isMountedRef.current = false;
        stopVoiceMode();
      };
    }, []);
    (0, import_react13.useEffect)(() => {
      const onError = (msg, url, line, col, err) => {
        sendTelemetry({ location: "window.onerror", message: "Uncaught error", data: { message: String(msg), url, line, col, errorMessage: err?.message }, timestamp: Date.now(), runId: "run1", hypothesisId: "H3" });
      };
      const onUnhandledRejection = (ev) => {
        sendTelemetry({ location: "unhandledrejection", message: "Unhandled promise rejection", data: { reason: String(ev?.reason?.message || ev?.reason) }, timestamp: Date.now(), runId: "run1", hypothesisId: "H4" });
      };
      window.addEventListener("error", (e) => {
        onError(e.message, e.filename, e.lineno, e.colno, e.error);
      });
      window.addEventListener("unhandledrejection", onUnhandledRejection);
      return () => {
        window.removeEventListener("error", onError);
        window.removeEventListener("unhandledrejection", onUnhandledRejection);
      };
    }, []);
    const [isConnected, setIsConnected] = (0, import_react13.useState)(null);
    const [connectionError, setConnectionError] = (0, import_react13.useState)(null);
    const [connectionRetryCount, setConnectionRetryCount] = (0, import_react13.useState)(0);
    const [shouldRetry, setShouldRetry] = (0, import_react13.useState)(false);
    const [editingMessageId, setEditingMessageId] = (0, import_react13.useState)(null);
    const [editingTripId, setEditingTripId] = (0, import_react13.useState)(null);
    const [editingTripName, setEditingTripName] = (0, import_react13.useState)("");
    const abortControllerRef = (0, import_react13.useRef)(null);
    const sendInProgressRef = (0, import_react13.useRef)(false);
    const completedProcessedRef = (0, import_react13.useRef)(false);
    const [agentStatus, setAgentStatus] = (0, import_react13.useState)(null);
    const [editModeMessageForRerun, setEditModeMessageForRerun] = (0, import_react13.useState)(null);
    const [isEditMode, setIsEditMode] = (0, import_react13.useState)(() => {
      try {
        const editStr = localStorage.getItem("edit_booking_context");
        if (!editStr) return false;
        const edit = JSON.parse(editStr);
        return edit?.action === "edit_trip";
      } catch (_) {
        return false;
      }
    });
    const [editReplaceBookingId, setEditReplaceBookingId] = (0, import_react13.useState)(null);
    const [chatMode, setChatMode] = (0, import_react13.useState)(() => {
      try {
        const editStr = localStorage.getItem("edit_booking_context");
        if (editStr) {
          try {
            const edit = JSON.parse(editStr);
            if (edit?.action === "edit_trip") return "normal";
          } catch (_) {
          }
        }
        const saved = localStorage.getItem("chat_mode");
        return saved === "agent" ? "agent" : "normal";
      } catch (_) {
        return "normal";
      }
    });
    (0, import_react13.useEffect)(() => {
      if (isEditMode && chatMode !== "normal") {
        setChatMode("normal");
        localStorage.setItem("chat_mode", "normal");
      }
    }, [isEditMode, chatMode]);
    const [isChatModeDropdownOpen, setIsChatModeDropdownOpen] = (0, import_react13.useState)(false);
    const chatModeDropdownRef = (0, import_react13.useRef)(null);
    (0, import_react13.useEffect)(() => {
      const handleClickOutside = (event) => {
        if (chatModeDropdownRef.current && !chatModeDropdownRef.current.contains(event.target)) {
          setIsChatModeDropdownOpen(false);
        }
      };
      if (isChatModeDropdownOpen) {
        document.addEventListener("mousedown", handleClickOutside);
      }
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }, [isChatModeDropdownOpen]);
    const [isSidebarOpen, setIsSidebarOpen] = (0, import_react13.useState)(() => {
      return typeof window !== "undefined" && window.innerWidth > 768;
    });
    const [selectedPlan, setSelectedPlan] = (0, import_react13.useState)(null);
    const [selectedTravelSlots, setSelectedTravelSlots] = (0, import_react13.useState)(null);
    const [latestPlanChoices, setLatestPlanChoices] = (0, import_react13.useState)([]);
    const [latestBotMessage, setLatestBotMessage] = (0, import_react13.useState)(null);
    const [messageIdsWithFlightSelected, setMessageIdsWithFlightSelected] = (0, import_react13.useState)(() => /* @__PURE__ */ new Set());
    const [messageIdsWithHotelSelected, setMessageIdsWithHotelSelected] = (0, import_react13.useState)(() => /* @__PURE__ */ new Set());
    const [messageIdsWithOutboundSelected, setMessageIdsWithOutboundSelected] = (0, import_react13.useState)(() => /* @__PURE__ */ new Set());
    (0, import_react13.useEffect)(() => {
      const handleResize = () => {
        if (window.innerWidth > 768) {
          setIsSidebarOpen(true);
        } else {
          setIsSidebarOpen(false);
        }
      };
      window.addEventListener("resize", handleResize);
      return () => window.removeEventListener("resize", handleResize);
    }, []);
    const touchStartRef = (0, import_react13.useRef)(null);
    const touchEndRef = (0, import_react13.useRef)(null);
    (0, import_react13.useEffect)(() => {
      const handleResize = () => {
        if (window.innerWidth <= 768) {
          setIsSidebarOpen(false);
        } else {
          setIsSidebarOpen(true);
        }
      };
      handleResize();
      window.addEventListener("resize", handleResize);
      return () => window.removeEventListener("resize", handleResize);
    }, []);
    const [isBooking, setIsBooking] = (0, import_react13.useState)(false);
    const [bookingResult, setBookingResult] = (0, import_react13.useState)(null);
    const [existingBookingForTripId, setExistingBookingForTripId] = (0, import_react13.useState)(null);
    (0, import_react13.useEffect)(() => {
      const trip = activeChat;
      const tripId = trip?.tripId || trip?.chatId;
      if (!tripId || !userId) {
        setExistingBookingForTripId(null);
        return;
      }
      let cancelled = false;
      fetch(`${API_BASE_URL}/api/booking/by-trip?trip_id=${encodeURIComponent(tripId)}`, { credentials: "include" }).then((res) => cancelled ? null : res.json()).then((data) => {
        if (cancelled) return;
        const hasBooking = data && (data._id || data.booking_id) && data.status !== "cancelled";
        setExistingBookingForTripId(hasBooking ? tripId : null);
      }).catch(() => {
        if (!cancelled) setExistingBookingForTripId(null);
      });
      return () => {
        cancelled = true;
      };
    }, [activeChat?.tripId, activeChat?.chatId, userId]);
    const activeTrip = activeChat;
    const lastUserMessageId = (0, import_react13.useMemo)(() => {
      const last = [...activeTrip?.messages || []].slice().reverse().find((m) => m.type === "user");
      return last?.id;
    }, [activeTrip]);
    const messages = (0, import_react13.useMemo)(() => {
      if (activeTrip?.messages && activeTrip.messages.length > 0) {
        return activeTrip.messages;
      }
      if (activeTripId) {
        try {
          const savedTrips = localStorage.getItem(LS_TRIPS_KEY);
          if (savedTrips) {
            const allTrips = JSON.parse(savedTrips);
            const currentUserId = user?.id || userId;
            const userTrips2 = allTrips.filter((t2) => {
              const tripUserId = t2.userId || t2.user_id;
              return !tripUserId || tripUserId === currentUserId;
            });
            const trip = userTrips2.find((t2) => t2.tripId === activeTripId || t2.chatId === activeTripId);
            if (trip?.messages && trip.messages.length > 0) {
              console.log(`\u2705 Restored ${trip.messages.length} messages from localStorage for trip: ${activeTripId}`);
              return trip.messages;
            }
          }
        } catch (e) {
          console.warn("Failed to restore messages from localStorage:", e);
        }
      }
      return [];
    }, [activeTrip?.messages, activeTripId, user?.id, userId]);
    const tripsRef = (0, import_react13.useRef)(trips);
    tripsRef.current = trips;
    (0, import_react13.useEffect)(() => {
      const saveTripsToStorage = () => {
        try {
          const current = tripsRef.current;
          if (!current?.length) return;
          const currentUserId = user?.id || userId;
          const userTrips2 = current.map((trip) => {
            const cid = trip.chatId || trip.tripId;
            const cached = historyCache.current?.get(cid);
            const stateMs = trip.messages || [];
            const bestMs = stateMs.length > 0 ? stateMs : cached?.length > 0 ? cached : [];
            return {
              ...trip,
              messages: bestMs.slice(-100),
              userId: currentUserId
            };
          });
          localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(userTrips2));
        } catch (_) {
        }
      };
      const onBeforeUnload = () => {
        saveTripsToStorage();
      };
      window.addEventListener("beforeunload", onBeforeUnload);
      return () => {
        window.removeEventListener("beforeunload", onBeforeUnload);
        saveTripsToStorage();
      };
    }, [user?.id, userId]);
    (0, import_react13.useEffect)(() => {
      const currentUserId = user?.id || userId;
      const userTrips2 = trips.filter((t2) => {
        const tripUserId = t2.userId || t2.user_id;
        return !tripUserId || tripUserId === currentUserId;
      });
      if (!activeTripId && userTrips2.length > 0) {
        const savedActiveTripId = localStorage.getItem(LS_ACTIVE_TRIP_KEY);
        if (savedActiveTripId && userTrips2.some((t2) => t2.tripId === savedActiveTripId || t2.chatId === savedActiveTripId)) {
          console.log(`\u2705 Restored activeTripId from localStorage: ${savedActiveTripId}`);
          setActiveTripId(savedActiveTripId);
          return;
        }
        console.log(`\u{1F3AF} Auto-selecting first trip (no activeTripId): ${userTrips2[0].tripId}, messages: ${userTrips2[0].messages?.length || 0}`);
        setActiveTripId(userTrips2[0].chatId || userTrips2[0].tripId);
        return;
      }
      if (activeTripId && !userTrips2.some((t2) => t2.tripId === activeTripId || t2.chatId === activeTripId) && userTrips2.length > 0) {
        console.log(`\u26A0\uFE0F Active trip not found (${activeTripId}), switching to first trip: ${userTrips2[0].tripId}`);
        setActiveTripId(userTrips2[0].chatId || userTrips2[0].tripId);
      }
    }, [activeTripId, trips, user?.id, userId]);
    (0, import_react13.useEffect)(() => {
      try {
        if (activeTripId) localStorage.setItem(LS_ACTIVE_TRIP_KEY, activeTripId);
      } catch (_) {
      }
    }, [activeTripId]);
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    (0, import_react13.useEffect)(() => {
      scrollToBottom();
    }, [activeTripId, messages.length]);
    const DEBUG_CHAT = import_meta.env.VITE_DEBUG_CHAT === "true";
    const checkApiConnection = import_react13.default.useCallback(async () => {
      if (DEBUG_CHAT) console.log("\u{1F50D} Checking API connection...", API_BASE_URL);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15e3);
      try {
        const response = await fetch(`${API_BASE_URL}/health`, {
          cache: "no-cache",
          method: "GET",
          headers: {
            "Accept": "application/json"
          },
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (!response.ok) {
          let healthBody = {};
          try {
            healthBody = await response.json();
          } catch (_) {
          }
          const checksMsg = healthBody?.checks?.startup?.message || healthBody?.checks?.mongodb?.message;
          if (DEBUG_CHAT || response.status === 503) {
            console.warn(`\u274C Health check failed: HTTP ${response.status}`, checksMsg ? `\u2014 ${checksMsg}` : "");
          }
          const fallbackController = new AbortController();
          const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), 5e3);
          try {
            const fallbackResponse = await fetch(`${API_BASE_URL}/`, {
              cache: "no-cache",
              signal: fallbackController.signal
            });
            clearTimeout(fallbackTimeoutId);
            if (fallbackResponse.ok) {
              console.log("\u2705 Fallback check: Backend is reachable (health reported degraded/unhealthy)");
              setIsConnected(true);
              setConnectionError(null);
              return;
            }
          } catch (fallbackError) {
            clearTimeout(fallbackTimeoutId);
            console.error("\u274C Fallback check also failed:", fallbackError);
          }
          setIsConnected(false);
          setConnectionError(
            response.status === 503 && checksMsg ? `\u0E40\u0E0B\u0E34\u0E23\u0E4C\u0E1F\u0E40\u0E27\u0E2D\u0E23\u0E4C\u0E23\u0E32\u0E22\u0E07\u0E32\u0E19: ${checksMsg} \u0E01\u0E23\u0E38\u0E13\u0E32\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A MongoDB \u0E2B\u0E23\u0E37\u0E2D\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E43\u0E19\u0E20\u0E32\u0E22\u0E2B\u0E25\u0E31\u0E07` : "\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E01\u0E31\u0E1A\u0E40\u0E0B\u0E34\u0E23\u0E4C\u0E1F\u0E40\u0E27\u0E2D\u0E23\u0E4C \u2014 \u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E27\u0E48\u0E32 Backend \u0E23\u0E31\u0E19\u0E2D\u0E22\u0E39\u0E48 (\u0E40\u0E0A\u0E48\u0E19 \u0E1E\u0E2D\u0E23\u0E4C\u0E15 8000) \u0E41\u0E25\u0E30 VITE_API_BASE_URL \u0E16\u0E39\u0E01\u0E15\u0E49\u0E2D\u0E07"
          );
          return;
        }
        const data = await response.json();
        if (DEBUG_CHAT) console.log("\u2705 Health check response:", data);
        const isHealthy = data.status === "healthy" || data.status === "ok" || data.status === "degraded" || data.status && data.status !== "unhealthy";
        if (DEBUG_CHAT) console.log(`\u{1F4CA} Connection status: ${isHealthy ? "\u2705 CONNECTED" : "\u274C DISCONNECTED"} (status: ${data.status})`);
        setIsConnected(isHealthy);
        if (isHealthy) setConnectionError(null);
        if (!isHealthy) {
          console.warn("\u26A0\uFE0F Backend status is not healthy:", data.status);
          if (data.checks) {
            console.warn("\u26A0\uFE0F Service checks:", data.checks);
          }
        } else if (data.status === "degraded") {
          console.warn("\u26A0\uFE0F Backend is degraded (some services slow/unavailable but operational)");
          if (data.checks) {
            console.warn("\u26A0\uFE0F Service checks:", data.checks);
          }
        }
      } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === "AbortError" || error.name === "TimeoutError") {
          console.warn("\u23F1\uFE0F Health check timed out (15s), backend may be slow but assuming reachable");
          return;
        }
        console.error("\u274C API connection error:", error);
        if (error.message && !error.message.includes("timeout") && !error.message.includes("aborted")) {
          console.error("\u274C Setting connection status to DISCONNECTED");
          setIsConnected(false);
          setConnectionError(
            "\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E01\u0E31\u0E1A\u0E40\u0E0B\u0E34\u0E23\u0E4C\u0E1F\u0E40\u0E27\u0E2D\u0E23\u0E4C (Failed to fetch) \u2014 \u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E27\u0E48\u0E32 Backend \u0E23\u0E31\u0E19\u0E2D\u0E22\u0E39\u0E48 \u0E41\u0E25\u0E30 VITE_API_BASE_URL \u0E16\u0E39\u0E01\u0E15\u0E49\u0E2D\u0E07 (\u0E40\u0E0A\u0E48\u0E19 http://localhost:8000)"
          );
        }
      }
    }, [API_BASE_URL]);
    (0, import_react13.useEffect)(() => {
      if (DEBUG_CHAT) console.log("\u{1F680} Initializing health check...");
      checkApiConnection();
      const interval = setInterval(() => {
        if (DEBUG_CHAT) console.log("\u{1F504} Periodic health check...");
        checkApiConnection();
      }, 1e4);
      return () => {
        if (DEBUG_CHAT) console.log("\u{1F6D1} Cleaning up health check interval");
        clearInterval(interval);
      };
    }, [checkApiConnection]);
    const formatMessageText = (text) => {
      if (!text) return "";
      if (typeof text === "object") {
        if (text.response && typeof text.response === "string") {
          return text.response;
        }
        if (text.message && typeof text.message === "string") {
          return text.message;
        }
        try {
          return JSON.stringify(text, null, 2);
        } catch {
          return "[\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E41\u0E2A\u0E14\u0E07\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E44\u0E14\u0E49]";
        }
      }
      let raw = String(text).trim();
      if (raw.startsWith("```")) {
        raw = raw.replace(/^```(?:json)?\s*/i, "");
        if (raw.endsWith("```")) raw = raw.slice(0, -3).trim();
      }
      if (raw.startsWith("{") && raw.endsWith("}") || raw.startsWith("[") && raw.endsWith("]")) {
        try {
          const obj = JSON.parse(raw);
          if (typeof obj === "string") return obj;
          if (obj && typeof obj === "object" && typeof obj.response === "string") {
            return obj.response;
          }
        } catch {
          return text;
        }
      }
      return text;
    };
    const toMessageText = (val) => {
      if (val == null) return "";
      if (typeof val === "string") return val;
      if (typeof val === "object") {
        if (typeof val.response === "string") return val.response;
        if (typeof val.message === "string") return val.message;
        try {
          return JSON.stringify(val, null, 2);
        } catch {
          return "[\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E41\u0E2A\u0E14\u0E07\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E44\u0E14\u0E49]";
        }
      }
      return String(val);
    };
    const appendMessageToTrip = (tripId, msg) => {
      if (!tripId || !msg) {
        console.warn("\u26A0\uFE0F appendMessageToTrip: tripId or msg is missing", { tripId, msg });
        return;
      }
      setTrips((prev) => {
        const currentUserId = user?.id || userId;
        return prev.map((t2) => {
          const tripUserId = t2.userId || t2.user_id;
          if (tripUserId && tripUserId !== currentUserId) return t2;
          if (t2.tripId !== tripId && t2.chatId !== tripId) return t2;
          const currentMessages = Array.isArray(t2.messages) ? t2.messages : [];
          if (msg.id && currentMessages.some((m) => m.id === msg.id)) {
            return t2;
          }
          if (msg.type === "bot" && currentMessages.length > 0) {
            const last = currentMessages[currentMessages.length - 1];
            if (last.type === "bot" && (last.text || "") === (msg.text || "")) {
              const nextMessages2 = [...currentMessages.slice(0, -1), msg];
              const cid2 = t2.chatId || t2.tripId;
              historyCache.current.set(cid2, nextMessages2);
              return { ...t2, messages: nextMessages2, updatedAt: nowISO() };
            }
          }
          const nextMessages = [...currentMessages, msg];
          const cid = t2.chatId || t2.tripId;
          historyCache.current.set(cid, nextMessages);
          return { ...t2, messages: nextMessages, updatedAt: nowISO() };
        });
      });
    };
    const updateMessageBookingResult = (tripId, result) => {
      if (!tripId || !result) return;
      setTrips((prev) => {
        const currentUserId = user?.id || userId;
        return prev.map((t2) => {
          const tripUserId = t2.userId || t2.user_id;
          if (tripUserId && tripUserId !== currentUserId) return t2;
          if (t2.tripId !== tripId && t2.chatId !== tripId) return t2;
          const messages2 = Array.isArray(t2.messages) ? t2.messages : [];
          const withIndex = messages2.map((m, i) => ({ m, i }));
          const last = withIndex.slice().reverse().find(({ m }) => m.type === "bot" && (m.currentPlan || m.travelSlots));
          if (!last) return t2;
          const newMessages = messages2.slice();
          newMessages[last.i] = { ...newMessages[last.i], bookingResult: result };
          return { ...t2, messages: newMessages, updatedAt: (/* @__PURE__ */ new Date()).toISOString() };
        });
      });
    };
    const setTripTitle = (tripId, title) => {
      if (!title) return;
      setTrips((prev) => {
        const currentUserId = user?.id || userId;
        return prev.map((t2) => {
          const tripUserId = t2.userId || t2.user_id;
          if (tripUserId && tripUserId !== currentUserId) {
            return t2;
          }
          if (t2.tripId !== tripId) return t2;
          return { ...t2, title, updatedAt: nowISO() };
        });
      });
    };
    const minSwipeDistance = 50;
    const onTouchStart = (e) => {
      if (window.innerWidth > 768) return;
      touchEndRef.current = null;
      touchStartRef.current = e.targetTouches[0].clientX;
    };
    const onTouchMove = (e) => {
      if (window.innerWidth > 768) return;
      touchEndRef.current = e.targetTouches[0].clientX;
    };
    const onTouchEnd = () => {
      if (window.innerWidth > 768) return;
      if (!touchStartRef.current || !touchEndRef.current) return;
      const distance = touchStartRef.current - touchEndRef.current;
      const isLeftSwipe = distance > minSwipeDistance;
      const isRightSwipe = distance < -minSwipeDistance;
      if (isLeftSwipe && isSidebarOpen) {
        setIsSidebarOpen(false);
      } else if (isRightSwipe && !isSidebarOpen) {
        setIsSidebarOpen(true);
      }
    };
    const handleRefreshHistory = async () => {
      if (isRefreshingRef.current) return;
      isRefreshingRef.current = true;
      setIsRefreshingHistory(true);
      try {
        const currentUserId = user?.id || userId;
        const headers = { "Content-Type": "application/json" };
        if (currentUserId) headers["X-User-ID"] = currentUserId;
        const res = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
          headers,
          credentials: "include"
        });
        if (!res.ok) {
          console.warn("\u26A0\uFE0F Failed to fetch sessions:", res.status);
          return;
        }
        const data = await res.json();
        const backendSessions = data.sessions || [];
        console.log(`\u2705 Fetched ${backendSessions.length} sessions from backend`);
        const backendTrips = backendSessions.map((session) => ({
          tripId: session.trip_id || session.chat_id,
          chatId: session.chat_id || session.session_id?.split("::")?.[1] || session.session_id,
          title: session.title || "\u0E41\u0E0A\u0E17\u0E43\u0E2B\u0E21\u0E48",
          updatedAt: session.last_updated || session.created_at,
          messages: [],
          userId: currentUserId,
          pinned: false
        }));
        loadedTripsRef.current.clear();
        setTrips((prev) => {
          const userTrips2 = prev.filter((t2) => {
            const tUserId = t2.userId || t2.user_id;
            return !tUserId || tUserId === currentUserId;
          });
          const existingChatIds = new Set(backendTrips.map((t2) => t2.chatId));
          const localOnlyTrips = userTrips2.filter((t2) => !existingChatIds.has(t2.chatId || t2.tripId));
          const merged = backendTrips.map((bt) => {
            const existing = userTrips2.find((t2) => (t2.chatId || t2.tripId) === bt.chatId);
            return existing ? { ...bt, pinned: existing.pinned || false } : bt;
          });
          return [...merged, ...localOnlyTrips];
        });
        if (activeTripId) {
          const chatId = activeChat?.chatId || activeTripId;
          const tripId = activeChat?.tripId || activeTripId;
          if (chatId) {
            try {
              setIsLoadingHistory(true);
              const histHeaders = { "Content-Type": "application/json", "X-Trip-ID": tripId || chatId };
              if (currentUserId) histHeaders["X-User-ID"] = currentUserId;
              const histRes = await fetch(`${API_BASE_URL}/api/chat/history/${chatId}`, {
                headers: histHeaders,
                credentials: "include"
              });
              if (histRes.ok) {
                const histData = await histRes.json();
                const restoredMessages = mapHistoryToMessages(histData);
                if (restoredMessages && restoredMessages.length > 0) {
                  loadedTripsRef.current.add(chatId);
                  setTrips((prev) => {
                    const idx = prev.findIndex((t2) => (t2.chatId || t2.tripId) === chatId);
                    if (idx === -1) return prev;
                    const newTrips = [...prev];
                    newTrips[idx] = { ...newTrips[idx], messages: restoredMessages, updatedAt: nowISO() };
                    return newTrips;
                  });
                }
              }
            } catch (e) {
              console.error("\u274C Error reloading active chat history:", e);
            } finally {
              setIsLoadingHistory(false);
            }
          }
        }
      } catch (error) {
        console.error("\u274C Error refreshing sessions:", error);
      } finally {
        isRefreshingRef.current = false;
        setIsRefreshingHistory(false);
      }
    };
    (0, import_react13.useEffect)(() => {
      if (!user?.id) return;
      const currentUserId = user?.id || userId;
      const initialSync = setTimeout(() => {
        if (!isRefreshingRef.current) {
          handleRefreshHistory();
        }
      }, 500);
      const flushSessionToMongo = () => {
        if (!currentUserId) return;
        const url = `${API_BASE_URL}/api/chat/flush-session`;
        try {
          fetch(url, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-User-ID": currentUserId
            },
            body: JSON.stringify({ session_id: null }),
            // flush all user sessions
            keepalive: true,
            credentials: "include"
          }).catch(() => {
          });
        } catch (e) {
        }
        if (activeTripId) {
          try {
            sessionStorage.setItem("ai_travel_last_active_trip", activeTripId);
          } catch (e) {
          }
        }
      };
      window.addEventListener("beforeunload", flushSessionToMongo);
      return () => {
        clearTimeout(initialSync);
        window.removeEventListener("beforeunload", flushSessionToMongo);
        flushSessionToMongo();
      };
    }, [user?.id]);
    const handleNewTrip = () => {
      try {
        console.log("\u{1F195} Creating new trip...");
        const displayName = user?.first_name || user?.name || "\u0E04\u0E38\u0E13";
        const currentUserId = user?.id || userId;
        const nt = createNewTrip("\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48", displayName);
        nt.userId = currentUserId;
        console.log("\u2705 New trip created:", { tripId: nt.tripId, chatId: nt.chatId, userId: currentUserId });
        ensureTripRegistered(nt.tripId, "\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48").then(() => fetchUserTrips());
        setTrips((prev) => {
          const userTrips2 = prev.filter((t2) => {
            const tripUserId = t2.userId || t2.user_id;
            return !tripUserId || tripUserId === currentUserId;
          });
          const newTrips = [nt, ...userTrips2];
          return newTrips;
        });
        setActiveTripId(nt.chatId);
        setInputText("");
        console.log("\u{1F504} Resetting backend chat context...");
        fetch(`${API_BASE_URL}/api/chat/reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            user_id: userId,
            chat_id: nt.chatId,
            // ✅ ใช้ chat_id แทน client_trip_id
            client_trip_id: nt.tripId
            // ✅ เก็บไว้สำหรับ backward compatibility
          })
        }).then((response) => {
          if (response.ok) {
            console.log("\u2705 Backend chat context reset successfully");
          } else {
            console.warn("\u26A0\uFE0F Backend reset failed:", response.status);
          }
        }).catch((error) => {
          console.error("\u274C Backend reset error:", error);
        });
      } catch (error) {
        console.error("\u274C Error creating new trip:", error);
        alert("\u0E40\u0E01\u0E34\u0E14\u0E02\u0E49\u0E2D\u0E1C\u0E34\u0E14\u0E1E\u0E25\u0E32\u0E14\u0E43\u0E19\u0E01\u0E32\u0E23\u0E2A\u0E23\u0E49\u0E32\u0E07\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E25\u0E2D\u0E07\u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07");
      }
    };
    const handleDeleteTrip = async (tripId) => {
      const result = await import_sweetalert2.default.fire({
        title: "\u0E25\u0E1A\u0E41\u0E0A\u0E17?",
        text: "\u0E04\u0E38\u0E13\u0E15\u0E49\u0E2D\u0E07\u0E01\u0E32\u0E23\u0E25\u0E1A\u0E41\u0E0A\u0E17\u0E19\u0E35\u0E49\u0E2D\u0E2D\u0E01\u0E08\u0E32\u0E01\u0E1B\u0E23\u0E30\u0E27\u0E31\u0E15\u0E34\u0E43\u0E0A\u0E48\u0E44\u0E2B\u0E21? \u0E01\u0E32\u0E23\u0E01\u0E23\u0E30\u0E17\u0E33\u0E19\u0E35\u0E49\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E22\u0E49\u0E2D\u0E19\u0E01\u0E25\u0E31\u0E1A\u0E44\u0E14\u0E49",
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#dc2626",
        cancelButtonColor: "#6b7280",
        confirmButtonText: "\u0E25\u0E1A",
        cancelButtonText: "\u0E22\u0E01\u0E40\u0E25\u0E34\u0E01",
        reverseButtons: true
      });
      if (!result.isConfirmed) return;
      const currentUserId = user?.id || userId;
      const userTrips2 = trips.filter((t2) => {
        const tripUserId = t2.userId || t2.user_id;
        return !tripUserId || tripUserId === currentUserId;
      });
      const tripToDelete = userTrips2.find((t2) => t2.tripId === tripId || t2.chatId === tripId);
      const chatIdToDelete = tripToDelete?.chatId || tripToDelete?.tripId || tripId;
      loadedTripsRef.current.delete(chatIdToDelete);
      loadedTripsRef.current.delete(tripId);
      historyCache.current.delete(chatIdToDelete);
      historyCache.current.delete(tripId);
      let backendOk = false;
      if (chatIdToDelete) {
        try {
          const res = await fetch(`${API_BASE_URL}/api/chat/sessions/${chatIdToDelete}`, {
            method: "DELETE",
            credentials: "include",
            headers: { "X-User-ID": currentUserId || "" }
          });
          backendOk = res.ok;
          if (!res.ok) console.warn(`\u26A0\uFE0F Backend delete failed: ${res.status}`);
        } catch (err) {
          console.error("\u274C Backend delete error:", err);
        }
      }
      setTrips((prev) => {
        const filtered = prev.filter((t2) => {
          const tUserId = t2.userId || t2.user_id;
          if (tUserId && tUserId !== currentUserId) return true;
          return t2.tripId !== tripId;
        });
        const remaining = filtered.filter((t2) => {
          const tUserId = t2.userId || t2.user_id;
          return !tUserId || tUserId === currentUserId;
        });
        let nextTrips;
        if (remaining.length === 0) {
          const displayName = user?.first_name || user?.name || "\u0E04\u0E38\u0E13";
          const newTrip = createNewTrip("\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48", displayName);
          newTrip.userId = currentUserId;
          nextTrips = [newTrip];
        } else {
          nextTrips = filtered;
        }
        localStorage.setItem(LS_TRIPS_KEY, JSON.stringify(nextTrips));
        return nextTrips;
      });
      const isActiveTrip = userTrips2.some(
        (t2) => t2.tripId === tripId && activeTripId === t2.tripId || t2.chatId === activeTripId && t2.tripId === tripId
      );
      if (isActiveTrip) {
        const remaining = userTrips2.filter((t2) => t2.tripId !== tripId);
        setActiveTripId(remaining[0]?.chatId || remaining[0]?.tripId || null);
      }
      if (backendOk) console.log(`\u2705 Deleted chat from backend + localStorage: ${chatIdToDelete}`);
    };
    const handleEditTripName = (tripId, currentTitle) => {
      setEditingTripId(tripId);
      setEditingTripName(currentTitle || "\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E21\u0E48");
    };
    const handleSaveTripName = (tripId) => {
      if (!editingTripName.trim()) {
        setEditingTripId(null);
        return;
      }
      setTrips((prev) => {
        const currentUserId = user?.id || userId;
        return prev.map((t2) => {
          const tripUserId = t2.userId || t2.user_id;
          if (tripUserId && tripUserId !== currentUserId) {
            return t2;
          }
          return t2.tripId === tripId ? { ...t2, title: editingTripName.trim(), updatedAt: nowISO() } : t2;
        });
      });
      setEditingTripId(null);
      setEditingTripName("");
    };
    const handleCancelEditTripName = () => {
      setEditingTripId(null);
      setEditingTripName("");
    };
    const handleTogglePin = (tripId) => {
      setTrips((prev) => {
        const currentUserId = user?.id || userId;
        return prev.map((t2) => {
          const tripUserId = t2.userId || t2.user_id;
          if (tripUserId && tripUserId !== currentUserId) {
            return t2;
          }
          return t2.tripId === tripId ? { ...t2, pinned: !t2.pinned, updatedAt: nowISO() } : t2;
        });
      });
    };
    const sortedTrips = (0, import_react13.useMemo)(() => {
      const currentUserId = user?.id || userId;
      const userTrips2 = trips.filter((t2) => {
        const tripUserId = t2.userId || t2.user_id;
        return !tripUserId || tripUserId === currentUserId;
      });
      if (!Array.isArray(userTrips2) || userTrips2.length === 0) return [];
      return [...userTrips2].sort((a, b) => {
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        try {
          const dateA = a.updatedAt ? new Date(a.updatedAt) : /* @__PURE__ */ new Date(0);
          const dateB = b.updatedAt ? new Date(b.updatedAt) : /* @__PURE__ */ new Date(0);
          return dateB.getTime() - dateA.getTime();
        } catch (e) {
          console.error("Error sorting trips by updatedAt:", e);
          return 0;
        }
      });
    }, [trips, user?.id, userId]);
    const handleStop = () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setProcessingTripId(null);
    };
    const handleEditMessage = (messageId, messageText) => {
      setEditingMessageId(messageId);
      setInputText(messageText);
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      }, 50);
    };
    const handleRefreshBot = async (userMessageId, userMessageText) => {
      if (isTyping) return;
      await regenerateFromUserText(userMessageId, userMessageText);
    };
    const sendMessage = async (textToSend) => {
      const trimmed = String(textToSend || "").trim();
      if (!trimmed) return;
      if (/จอง\s*เลย/.test(trimmed)) {
        setShowTripSummary(true);
      }
      if (sendInProgressRef.current) {
        console.warn("\u26A0\uFE0F sendMessage: already in progress, skipping duplicate send");
        return;
      }
      sendInProgressRef.current = true;
      completedProcessedRef.current = false;
      if (isConnected === false) {
        sendInProgressRef.current = false;
        alert('\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E01\u0E31\u0E1A\u0E40\u0E0B\u0E34\u0E23\u0E4C\u0E1F\u0E40\u0E27\u0E2D\u0E23\u0E4C \u0E01\u0E23\u0E38\u0E13\u0E32\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E27\u0E48\u0E32 Backend \u0E23\u0E31\u0E19\u0E2D\u0E22\u0E39\u0E48 (\u0E40\u0E0A\u0E48\u0E19 \u0E1E\u0E2D\u0E23\u0E4C\u0E15 8000) \u0E2B\u0E23\u0E37\u0E2D\u0E01\u0E14 "\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48" \u0E17\u0E35\u0E48\u0E41\u0E16\u0E1A\u0E41\u0E08\u0E49\u0E07\u0E40\u0E15\u0E37\u0E2D\u0E19\u0E14\u0E49\u0E32\u0E19\u0E1A\u0E19');
        return;
      }
      const tripId = activeTrip?.tripId;
      const targetId = activeTrip?.chatId || activeTrip?.tripId;
      if (!tripId || !targetId) {
        sendInProgressRef.current = false;
        return;
      }
      if (editingMessageId) {
        setTrips(
          (prev) => prev.map((t2) => {
            if (t2.tripId !== targetId && t2.chatId !== targetId) return t2;
            const msgIndex = t2.messages.findIndex((m) => m.id === editingMessageId);
            if (msgIndex === -1) return t2;
            const newMessages = t2.messages.slice(0, msgIndex);
            return { ...t2, messages: newMessages, updatedAt: nowISO() };
          })
        );
        setEditingMessageId(null);
      }
      const userMessage = {
        id: makeId("msg_user"),
        type: "user",
        text: trimmed
      };
      appendMessageToTrip(targetId, userMessage);
      setProcessingTripId(targetId);
      setAgentStatus(null);
      abortControllerRef.current = new AbortController();
      try {
        const chatId = activeTrip?.chatId || tripId;
        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Conversation-ID": chatId
            // ✅ ส่ง chat_id ใน header
          },
          credentials: "include",
          signal: abortControllerRef.current.signal,
          body: JSON.stringify({
            user_id: userId,
            message: trimmed,
            trigger: "user_message",
            trip_id: tripId,
            // ✅ trip_id: สำหรับ 1 ทริป
            chat_id: chatId,
            // ✅ chat_id: สำหรับแต่ละแชท
            client_trip_id: tripId,
            // ✅ เก็บไว้สำหรับ backward compatibility
            mode: chatMode
            // ✅ 'normal' หรือ 'agent'
          })
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;
            if (trimmedLine.startsWith("data: ")) {
              try {
                const data = JSON.parse(trimmedLine.slice(6));
                if (data.status === "error") {
                  sendTelemetry({
                    location: "AITravelChat.jsx:1050",
                    message: "SSE error received",
                    data: { error_message: data.message },
                    timestamp: Date.now(),
                    sessionId: "debug-session",
                    runId: "run1",
                    hypothesisId: "A"
                  });
                  throw new Error(data.message || "Unknown stream error");
                }
                if (data.status && data.message && data.status !== "heartbeat" && data.step !== "heartbeat") {
                  setAgentStatus({
                    status: data.status,
                    message: data.message,
                    step: data.step
                  });
                }
                if (data.status === "summary_ready" && data.current_plan) {
                  setSelectedPlan(data.current_plan);
                  if (data.travel_slots) setSelectedTravelSlots(data.travel_slots);
                  if (data.agent_state) setLatestBotMessage((prev) => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
                }
                if (data.status === "completed" && data.data) {
                  if (completedProcessedRef.current) {
                    console.warn("\u26A0\uFE0F SSE completed already processed for this request, skipping duplicate");
                    continue;
                  }
                  completedProcessedRef.current = true;
                  const finalData2 = data.data;
                  console.log("API data (completed) >>>", finalData2);
                  sendTelemetry({ location: "AITravelChat.jsx:completed", message: "SSE completed received", data: { has_current_plan: !!finalData2?.current_plan, auto_booked: finalData2?.auto_booked, will_set_selected_plan: !!finalData2?.current_plan }, timestamp: Date.now(), runId: "run1", hypothesisId: "H4" });
                  sendTelemetry({
                    location: "AITravelChat.jsx:1062",
                    message: "Received completed status",
                    data: { has_response: !!finalData2.response, response_length: finalData2.response?.length || 0, has_plan_choices: !!finalData2.plan_choices },
                    timestamp: Date.now(),
                    sessionId: "debug-session",
                    runId: "run1",
                    hypothesisId: "A"
                  });
                  let responseText = "";
                  if (finalData2?.auto_booked && finalData2?.agent_booking_success_message) {
                    responseText = finalData2.agent_booking_success_message;
                  } else if (typeof finalData2?.response === "string" && finalData2.response.trim()) {
                    responseText = finalData2.response.trim();
                  } else if (finalData2?.message && typeof finalData2.message === "string") {
                    responseText = finalData2.message.trim();
                  } else if (finalData2?.text && typeof finalData2.text === "string") {
                    responseText = finalData2.text.trim();
                  } else if (finalData2?.response) {
                    responseText = toMessageText(finalData2.response).trim();
                  }
                  if (!responseText) {
                    responseText = "\u0E44\u0E14\u0E49\u0E23\u0E31\u0E1A\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E15\u0E2D\u0E1A\u0E01\u0E25\u0E31\u0E1A\u0E41\u0E25\u0E49\u0E27 \u0E41\u0E15\u0E48\u0E44\u0E21\u0E48\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07";
                    console.warn("\u26A0\uFE0F No response text found in finalData:", finalData2);
                  }
                  const botMessage = {
                    id: makeId("msg_bot"),
                    type: "bot",
                    text: responseText,
                    debug: finalData2?.debug || null,
                    travelSlots: finalData2?.travel_slots || null,
                    searchResults: finalData2?.search_results || {},
                    planChoices: Array.isArray(finalData2?.plan_choices) ? finalData2.plan_choices : finalData2?.plan_choices ? [finalData2.plan_choices] : [],
                    agentState: finalData2?.agent_state || null,
                    suggestions: Array.isArray(finalData2?.suggestions) ? finalData2.suggestions : [],
                    currentPlan: finalData2?.current_plan || null,
                    tripTitle: finalData2?.trip_title || null,
                    slotIntent: finalData2?.slot_intent || null,
                    slotChoices: Array.isArray(finalData2?.slot_choices) ? finalData2.slot_choices : [],
                    reasoning: finalData2?.reasoning || null,
                    memorySuggestions: finalData2?.memory_suggestions || null,
                    cachedOptions: finalData2?.cached_options || null,
                    cacheValidation: finalData2?.cache_validation || null,
                    workflowValidation: finalData2?.workflow_validation || null
                  };
                  if (botMessage.planChoices && botMessage.planChoices.length > 0) {
                    console.log("\u{1F4CB} Plan choices received:", botMessage.planChoices.length, "choices");
                  }
                  if (botMessage.slotChoices && botMessage.slotChoices.length > 0) {
                    console.log("\u{1F3AF} Slot choices received:", botMessage.slotChoices.length, "choices, intent:", botMessage.slotIntent);
                    console.log("\u{1F3AF} Slot choices data:", botMessage.slotChoices);
                  } else {
                    console.log("\u26A0\uFE0F No slot choices received. finalData.slot_choices:", finalData2?.slot_choices);
                  }
                  appendMessageToTrip(targetId, botMessage);
                  setLatestBotMessage(botMessage);
                  const responseTextLower = botMessage.text?.toLowerCase() || "";
                  const isAgentModeBooking = chatMode === "agent" && (finalData2.auto_booked === true || responseTextLower.includes("\u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08") || responseTextLower.includes("\u0E08\u0E2D\u0E07\u0E40\u0E2A\u0E23\u0E47\u0E08") || responseTextLower.includes("\u0E2A\u0E23\u0E49\u0E32\u0E07\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08") || responseTextLower.includes("auto-booked") || responseTextLower.includes("my bookings"));
                  if (isAgentModeBooking) {
                    const accuracyScore = finalData2.agent_accuracy_score != null ? Number(finalData2.agent_accuracy_score) : null;
                    import_sweetalert2.default.fire({
                      icon: "success",
                      title: "\u2705 \u0E08\u0E2D\u0E07\u0E2D\u0E31\u0E15\u0E42\u0E19\u0E21\u0E31\u0E15\u0E34\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08",
                      html: `
                      <div style="text-align: left;">
                        <p style="margin-bottom: 12px;">Agent \u0E08\u0E2D\u0E07\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13\u0E40\u0E23\u0E35\u0E22\u0E1A\u0E23\u0E49\u0E2D\u0E22\u0E41\u0E25\u0E49\u0E27</p>
                        <p style="margin-bottom: 12px; color: #dc2626; font-weight: 600;">
                          \u26A0\uFE0F \u0E01\u0E23\u0E38\u0E13\u0E32\u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E17\u0E35\u0E48 My Bookings \u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07
                        </p>
                        <p style="margin-bottom: 0; color: #6b7280; font-size: 14px;">
                          \u{1F4CB} \u0E14\u0E39\u0E23\u0E32\u0E22\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E17\u0E35\u0E48 "\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E02\u0E2D\u0E07\u0E09\u0E31\u0E19"
                        </p>
                      </div>
                    `,
                      confirmButtonText: "\u0E44\u0E1B\u0E17\u0E35\u0E48 My Bookings",
                      cancelButtonText: "\u0E1B\u0E34\u0E14",
                      showCancelButton: true,
                      confirmButtonColor: "#2563eb",
                      cancelButtonColor: "#6b7280",
                      reverseButtons: true,
                      allowOutsideClick: true,
                      allowEscapeKey: true
                    }).then((result) => {
                      if (result.isConfirmed && onNavigateToBookings) {
                        onNavigateToBookings();
                      }
                      return showAgentEvaluationSwal(accuracyScore, chatId);
                    });
                  }
                  if (isVoiceModeRef.current && botMessage.text) {
                    const cleanText = botMessage.text.replace(/[🎯💡📋✅❌⏹️💙]/g, "").replace(/\*\*(.*?)\*\*/g, "$1").replace(/\*(.*?)\*/g, "$1").replace(/```[\s\S]*?```/g, "").replace(/`(.*?)`/g, "$1").trim();
                    if (cleanText) {
                      speakText(cleanText);
                    } else {
                      voiceAwaitingResponseRef.current = false;
                      if (!voiceAiSpeakingRef.current && recognitionRef.current) {
                        try {
                          recognitionRef.current.start();
                          setIsRecording(true);
                          setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
                        } catch (_) {
                        }
                      }
                    }
                  }
                  if (finalData2?.plan_choices) {
                    setLatestPlanChoices(finalData2.plan_choices);
                  }
                  if (finalData2?.current_plan) {
                    setSelectedPlan(finalData2.current_plan);
                    sendTelemetry({ location: "AITravelChat.jsx:setSelectedPlan", message: "setSelectedPlan called from current_plan", data: { has_current_plan: true }, timestamp: Date.now(), runId: "run1", hypothesisId: "H4" });
                    setSelectedTravelSlots(finalData2?.travel_slots || null);
                    if (finalData2.agent_state) {
                      setLatestBotMessage((prev) => prev ? { ...prev, agentState: finalData2.agent_state } : { agentState: finalData2.agent_state });
                    }
                    console.log("\u2705 TripPlan state synced from backend:", {
                      hasPlan: !!finalData2.current_plan,
                      hasSlots: !!finalData2.travel_slots,
                      step: finalData2.agent_state?.step
                    });
                  } else if (finalData2?.travel_slots) {
                    setSelectedTravelSlots(finalData2.travel_slots);
                    console.log("\u2705 Travel slots synced from backend");
                  }
                  if (finalData2.trip_title) {
                    setTripTitle(tripId, finalData2.trip_title);
                  }
                }
              } catch (err) {
                console.error("Error parsing SSE data line:", trimmedLine, err);
                sendTelemetry({ location: "AITravelChat.jsx:SSE parse catch", message: "SSE line parse error", data: { errorMessage: String(err?.message), linePreview: (trimmedLine || "").slice(0, 100) }, timestamp: Date.now(), runId: "run1", hypothesisId: "H2" });
              }
            }
          }
        }
      } catch (error) {
        console.error("Error calling API:", error);
        sendTelemetry({ location: "AITravelChat.jsx:sendMessage catch", message: "API/stream error", data: { errorName: error?.name, errorMessage: String(error?.message) }, timestamp: Date.now(), runId: "run1", hypothesisId: "H2" });
        if (error.name === "AbortError") {
          appendMessageToTrip(targetId, {
            id: Date.now() + 1,
            type: "bot",
            text: "\u23F9\uFE0F \u0E2B\u0E22\u0E38\u0E14\u0E01\u0E32\u0E23\u0E17\u0E33\u0E07\u0E32\u0E19\u0E41\u0E25\u0E49\u0E27\u0E04\u0E48\u0E30"
          });
        } else {
          setIsConnected(false);
          const isNetworkError = !error.message || /failed to fetch|connection reset|network error|ERR_CONNECTION/i.test(String(error.message));
          const shortMessage = "\u0E01\u0E32\u0E23\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E16\u0E39\u0E01\u0E15\u0E31\u0E14\u0E01\u0E25\u0E32\u0E07\u0E17\u0E32\u0E07 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E25\u0E2D\u0E07\u0E2A\u0E48\u0E07\u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07\u0E2B\u0E23\u0E37\u0E2D\u0E01\u0E14 Regenerate \u0E04\u0E48\u0E30";
          const longMessage = `\u274C \u0E40\u0E01\u0E34\u0E14\u0E02\u0E49\u0E2D\u0E1C\u0E34\u0E14\u0E1E\u0E25\u0E32\u0E14\u0E43\u0E19\u0E01\u0E32\u0E23\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D

${error.message}

\u0E42\u0E1B\u0E23\u0E14\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A:
1. Backend \u0E01\u0E33\u0E25\u0E31\u0E07\u0E17\u0E33\u0E07\u0E32\u0E19\u0E2D\u0E22\u0E39\u0E48
2. API Keys \u0E16\u0E39\u0E01\u0E15\u0E49\u0E2D\u0E07
3. \u0E01\u0E32\u0E23\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E2D\u0E34\u0E19\u0E40\u0E17\u0E2D\u0E23\u0E4C\u0E40\u0E19\u0E47\u0E15`;
          const errorMessage = {
            id: Date.now() + 1,
            type: "bot",
            text: isNetworkError ? `\u274C ${shortMessage}` : longMessage,
            error: true,
            retryAvailable: true,
            onRetry: () => {
              setShouldRetry(true);
              setConnectionRetryCount((prev) => prev + 1);
              setTimeout(() => {
                sendMessage(trimmed);
              }, 1e3 * Math.min(connectionRetryCount + 1, 5));
            }
          };
          appendMessageToTrip(targetId, errorMessage);
        }
        if (isVoiceModeRef.current) {
          voiceAwaitingResponseRef.current = false;
          if (!voiceAiSpeakingRef.current && !synthesisRef.current && recognitionRef.current) {
            try {
              recognitionRef.current.start();
              setIsRecording(true);
              setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
            } catch (_) {
            }
          }
        }
      } finally {
        setProcessingTripId(null);
        setAgentStatus(null);
        abortControllerRef.current = null;
        sendInProgressRef.current = false;
      }
    };
    const regenerateFromUserText = async (messageId, userText) => {
      const tripId = activeTrip?.tripId;
      const targetId = activeTrip?.chatId || activeTrip?.tripId;
      if (!tripId || !targetId) return;
      const trimmed = String(userText || "").trim();
      if (!trimmed) return;
      const now = Date.now();
      const lastAt = lastRefreshAtRef.current[messageId] || 0;
      if (now - lastAt < REFRESH_COOLDOWN_MS) return;
      lastRefreshAtRef.current[messageId] = now;
      setProcessingTripId(targetId);
      setTrips(
        (prev) => prev.map((t2) => {
          if (t2.tripId !== targetId && t2.chatId !== targetId) return t2;
          const msgIndex = t2.messages.findIndex((m) => m.id === messageId);
          if (msgIndex === -1) return t2;
          const newMessages = t2.messages.slice(0, msgIndex + 1);
          return { ...t2, messages: newMessages, updatedAt: nowISO() };
        })
      );
      abortControllerRef.current = new AbortController();
      setAgentStatus(null);
      try {
        const chatId = activeTrip?.chatId || tripId;
        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Conversation-ID": chatId
            // ✅ ส่ง chat_id ใน header
          },
          credentials: "include",
          signal: abortControllerRef.current.signal,
          body: JSON.stringify({
            user_id: userId,
            message: trimmed,
            trigger: "refresh",
            trip_id: tripId,
            // ✅ trip_id: สำหรับ 1 ทริป
            chat_id: chatId,
            // ✅ chat_id: สำหรับแต่ละแชท
            client_trip_id: tripId
            // ✅ เก็บไว้สำหรับ backward compatibility
          })
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;
            if (trimmedLine.startsWith("data: ")) {
              try {
                const data = JSON.parse(trimmedLine.slice(6));
                if (data.status === "error") {
                  throw new Error(data.message || "Unknown stream error");
                }
                if (data.status && data.message && data.status !== "heartbeat" && data.step !== "heartbeat") {
                  setAgentStatus({
                    status: data.status,
                    message: data.message,
                    step: data.step
                  });
                }
                if (data.status === "summary_ready" && data.current_plan) {
                  setSelectedPlan(data.current_plan);
                  if (data.travel_slots) setSelectedTravelSlots(data.travel_slots);
                  if (data.agent_state) setLatestBotMessage((prev) => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
                }
                if (data.status === "completed" && data.data) {
                  const finalData2 = data.data;
                  console.log("Refresh API data (completed) >>>", finalData2);
                  const botMessage = {
                    id: Date.now() + 1,
                    type: "bot",
                    text: toMessageText(finalData2.response),
                    debug: finalData2.debug || null,
                    travelSlots: finalData2.travel_slots || null,
                    searchResults: finalData2.search_results || {},
                    planChoices: Array.isArray(finalData2.plan_choices) ? finalData2.plan_choices : finalData2.plan_choices ? [finalData2.plan_choices] : [],
                    agentState: finalData2.agent_state || null,
                    suggestions: finalData2.suggestions || [],
                    currentPlan: finalData2.current_plan || null,
                    tripTitle: finalData2.trip_title || null,
                    slotIntent: finalData2.slot_intent || null,
                    slotChoices: finalData2.slot_choices || [],
                    reasoning: finalData2.reasoning || null,
                    memorySuggestions: finalData2.memory_suggestions || null,
                    cachedOptions: finalData2.cached_options || null,
                    cacheValidation: finalData2.cache_validation || null,
                    workflowValidation: finalData2.workflow_validation || null
                  };
                  appendMessageToTrip(targetId, botMessage);
                  if (isVoiceModeRef.current && botMessage.text) {
                    const cleanText = botMessage.text.replace(/[🎯💡📋✅❌⏹️💙]/g, "").replace(/\*\*(.*?)\*\*/g, "$1").replace(/\*(.*?)\*/g, "$1").replace(/```[\s\S]*?```/g, "").replace(/`(.*?)`/g, "$1").trim();
                    if (cleanText) speakText(cleanText);
                    else {
                      voiceAwaitingResponseRef.current = false;
                      if (!voiceAiSpeakingRef.current && recognitionRef.current) {
                        try {
                          recognitionRef.current.start();
                          setIsRecording(true);
                          setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
                        } catch (_) {
                        }
                      }
                    }
                  }
                  if (finalData2.plan_choices) setLatestPlanChoices(finalData2.plan_choices);
                  const agentState = finalData2.agent_state || {};
                  const slotWorkflow = agentState.slot_workflow || {};
                  const workflowValidation = finalData2.workflow_validation || agentState.workflow_validation || {};
                  const currentWorkflowStep = workflowValidation.current_step || agentState.step || "planning";
                  const isWorkflowComplete = workflowValidation.is_complete || false;
                  const workflowIssues = workflowValidation.completeness_issues || [];
                  if (currentWorkflowStep) {
                    console.log("\u{1F4CB} Current Workflow Step:", currentWorkflowStep, {
                      is_complete: isWorkflowComplete,
                      issues: workflowIssues.length
                    });
                  }
                  const isSlotWorkflowComplete = slotWorkflow.current_slot === "summary" || agentState.step === "trip_summary" || currentWorkflowStep === "trip_summary" || !slotWorkflow.current_slot && !finalData2.slot_choices && !finalData2.slot_intent;
                  const hasOnlyTransferPending = finalData2.slot_intent === "transfer" || finalData2.slot_intent === "transport";
                  const shouldShowSummary = isSlotWorkflowComplete && isWorkflowComplete || currentWorkflowStep === "trip_summary" && isWorkflowComplete || hasOnlyTransferPending;
                  const isAgentMode = finalData2.agent_state?.agent_mode || chatMode === "agent";
                  if (finalData2.current_plan) {
                    if (isAgentMode || shouldShowSummary) {
                      setSelectedPlan(finalData2.current_plan);
                      setSelectedTravelSlots(finalData2.travel_slots || null);
                      setShowTripSummary(true);
                      console.log("\u2705 Agent Mode: Auto-set selectedPlan from current_plan");
                    } else {
                      setSelectedPlan(finalData2.current_plan);
                      setSelectedTravelSlots(finalData2.travel_slots || null);
                      if (currentWorkflowStep === "trip_summary" || currentWorkflowStep === "completed") {
                        setShowTripSummary(true);
                      }
                    }
                  } else {
                    setSelectedPlan(null);
                    setSelectedTravelSlots(null);
                  }
                  if (finalData2.trip_title) setTripTitle(tripId, finalData2.trip_title);
                }
              } catch (err) {
                console.error("Error parsing SSE data line:", trimmedLine, err);
              }
            }
          }
        }
      } catch (e) {
        if (e.name === "AbortError") {
          appendMessageToTrip(targetId, {
            id: Date.now() + 1,
            type: "bot",
            text: "\u23F9\uFE0F \u0E2B\u0E22\u0E38\u0E14\u0E01\u0E32\u0E23\u0E17\u0E33\u0E07\u0E32\u0E19\u0E41\u0E25\u0E49\u0E27\u0E04\u0E48\u0E30"
          });
        } else {
          const isNetworkError = !e.message || /failed to fetch|connection reset|network error|ERR_CONNECTION/i.test(String(e.message));
          const text = isNetworkError ? "\u274C \u0E01\u0E32\u0E23\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E16\u0E39\u0E01\u0E15\u0E31\u0E14\u0E01\u0E25\u0E32\u0E07\u0E17\u0E32\u0E07 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E25\u0E2D\u0E07\u0E01\u0E14 Regenerate \u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07\u0E04\u0E48\u0E30" : `\u274C Error: ${e.message}`;
          if (isNetworkError) setIsConnected(false);
          appendMessageToTrip(targetId, {
            id: Date.now() + 1,
            type: "bot",
            text
          });
        }
        if (isVoiceModeRef.current) {
          voiceAwaitingResponseRef.current = false;
          if (!voiceAiSpeakingRef.current && !synthesisRef.current && recognitionRef.current) {
            try {
              recognitionRef.current.start();
              setIsRecording(true);
              setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
            } catch (_) {
            }
          }
        }
      } finally {
        setProcessingTripId(null);
        abortControllerRef.current = null;
      }
    };
    const didSetInitialPromptRef = (0, import_react13.useRef)(false);
    const didSendEditMessageRef = (0, import_react13.useRef)(false);
    (0, import_react13.useEffect)(() => {
      const editContextStr = localStorage.getItem("edit_booking_context");
      if (!editContextStr || !activeTripId || activeChat) return;
      try {
        const editContext = JSON.parse(editContextStr);
        if (editContext.action !== "edit_trip" || !editContext.tripId || !editContext.chatId) return;
        const tripId = editContext.tripId;
        const chatId = editContext.chatId || tripId;
        const currentUserId = user?.id || userId;
        setTrips((prev) => {
          const hasTrip = prev.some((t2) => (t2.chatId === chatId || t2.tripId === tripId) && (!t2.userId || t2.userId === currentUserId));
          if (hasTrip) return prev;
          return [...prev, {
            tripId,
            chatId,
            title: "\u0E17\u0E23\u0E34\u0E1B\u0E17\u0E35\u0E48\u0E08\u0E2D\u0E07",
            messages: [],
            userId: currentUserId,
            pinned: false,
            updatedAt: (/* @__PURE__ */ new Date()).toISOString()
          }];
        });
      } catch (e) {
        console.warn("Failed to add edit trip:", e);
      }
    }, [activeTripId, activeChat, user?.id, userId]);
    (0, import_react13.useEffect)(() => {
      if (didSendEditMessageRef.current) return;
      const editContextStr = localStorage.getItem("edit_booking_context");
      if (!editContextStr) return;
      if (!activeChat || !activeChat.tripId) {
        return;
      }
      try {
        const editContext = JSON.parse(editContextStr);
        if (editContext.action === "edit_trip" && editContext.booking) {
          setIsEditMode(true);
          setEditReplaceBookingId(editContext.bookingId || null);
          setChatMode("normal");
          localStorage.setItem("chat_mode", "normal");
          didSendEditMessageRef.current = true;
          const booking = editContext.booking;
          const travelSlots = booking.travel_slots || {};
          const origin = travelSlots.origin_city || travelSlots.origin || "";
          const destination = travelSlots.destination_city || travelSlots.destination || "";
          const route = origin && destination ? `${origin} \u2192 ${destination}` : "\u0E17\u0E23\u0E34\u0E1B\u0E19\u0E35\u0E49";
          const departureDate = travelSlots.departure_date || travelSlots.start_date || "";
          const returnDate = travelSlots.return_date || travelSlots.end_date || "";
          const totalPrice = booking.total_price || 0;
          const currency = booking.currency || "THB";
          const formattedPrice = formatPriceInThb(totalPrice, currency);
          const editMessage = `\u0E09\u0E31\u0E19\u0E15\u0E49\u0E2D\u0E07\u0E01\u0E32\u0E23\u0E41\u0E01\u0E49\u0E44\u0E02\u0E17\u0E23\u0E34\u0E1B\u0E17\u0E35\u0E48\u0E08\u0E2D\u0E07\u0E44\u0E27\u0E49

\u{1F4CB} \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E1B\u0E31\u0E08\u0E08\u0E38\u0E1A\u0E31\u0E19:
- \u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07: ${route}
${departureDate ? `- \u0E27\u0E31\u0E19\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07: ${departureDate}` : ""}${returnDate ? `
- \u0E27\u0E31\u0E19\u0E01\u0E25\u0E31\u0E1A: ${returnDate}` : ""}
- \u0E23\u0E32\u0E04\u0E32\u0E23\u0E27\u0E21: ${formattedPrice}
- Booking ID: ${editContext.bookingId}

\u0E01\u0E23\u0E38\u0E13\u0E32\u0E0A\u0E48\u0E27\u0E22\u0E09\u0E31\u0E19\u0E41\u0E01\u0E49\u0E44\u0E02\u0E17\u0E23\u0E34\u0E1B\u0E19\u0E35\u0E49\u0E14\u0E49\u0E27\u0E22\u0E04\u0E48\u0E30`;
          setEditModeMessageForRerun(editMessage);
          localStorage.removeItem("edit_booking_context");
          setTimeout(() => {
            if (activeChat && activeChat.tripId) {
              sendMessage(editMessage);
            }
          }, 1e3);
        }
      } catch (e) {
        console.error("Failed to parse edit context:", e);
        localStorage.removeItem("edit_booking_context");
      }
    }, [activeChat]);
    (0, import_react13.useEffect)(() => {
      if (!isEditMode || editModeMessageForRerun) return;
      const msgs = activeTrip?.messages || [];
      const editLike = msgs.slice().reverse().find((m) => m.type === "user" && (m.text || "").includes("\u0E09\u0E31\u0E19\u0E15\u0E49\u0E2D\u0E07\u0E01\u0E32\u0E23\u0E41\u0E01\u0E49\u0E44\u0E02\u0E17\u0E23\u0E34\u0E1B\u0E17\u0E35\u0E48\u0E08\u0E2D\u0E07\u0E44\u0E27\u0E49"));
      if (editLike && editLike.text) setEditModeMessageForRerun(editLike.text);
    }, [isEditMode, editModeMessageForRerun, activeTrip?.messages]);
    (0, import_react13.useEffect)(() => {
      if (didSetInitialPromptRef.current) return;
      const p = (initialPrompt || "").trim();
      if (!p) return;
      didSetInitialPromptRef.current = true;
      setInputText(p);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }, [initialPrompt]);
    const handleSend = async () => {
      if (!inputText.trim()) return;
      const currentInput = inputText;
      const correctionResult = correctTypos(currentInput);
      const languageMismatch = detectLanguageMismatch(currentInput, "thai");
      if (correctionResult.hasCorrections || languageMismatch.mismatch) {
        let suggestionText = "";
        let correctedText = currentInput;
        if (correctionResult.hasCorrections) {
          correctedText = correctionResult.corrected;
          const corrections = correctionResult.corrections.map(
            (c) => `"${c.original}" \u2192 "${c.corrected}"`
          ).join(", ");
          suggestionText += `\u0E1E\u0E1A\u0E04\u0E33\u0E17\u0E35\u0E48\u0E2D\u0E32\u0E08\u0E08\u0E30\u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E1C\u0E34\u0E14: ${corrections}

`;
        }
        if (languageMismatch.mismatch) {
          suggestionText += languageMismatch.suggestion + "\n\n";
        }
        suggestionText += `\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E17\u0E35\u0E48\u0E41\u0E01\u0E49\u0E44\u0E02\u0E41\u0E25\u0E49\u0E27:
"${correctedText}"`;
        const result = await import_sweetalert2.default.fire({
          title: "\u0E15\u0E23\u0E27\u0E08\u0E1E\u0E1A\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E17\u0E35\u0E48\u0E2D\u0E32\u0E08\u0E08\u0E30\u0E1C\u0E34\u0E14",
          text: suggestionText,
          icon: "info",
          showCancelButton: true,
          confirmButtonText: "\u0E43\u0E0A\u0E49\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E17\u0E35\u0E48\u0E41\u0E01\u0E49\u0E44\u0E02\u0E41\u0E25\u0E49\u0E27",
          cancelButtonText: "\u0E2A\u0E48\u0E07\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E40\u0E14\u0E34\u0E21",
          reverseButtons: true,
          customClass: {
            popup: "swal-custom-popup",
            title: "swal-custom-title",
            text: "swal-custom-text"
          }
        });
        if (result.isConfirmed) {
          setInputText("");
          setEditingMessageId(null);
          sendMessage(correctedText);
        } else if (result.dismiss === import_sweetalert2.default.DismissReason.cancel) {
          setInputText("");
          setEditingMessageId(null);
          sendMessage(currentInput);
        }
      } else {
        setInputText("");
        setEditingMessageId(null);
        sendMessage(currentInput);
      }
    };
    const handleKeyPress = (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    };
    const handleMemoryCommit = async (suggestion, messageId) => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/memory/commit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            user_id: userId,
            memory_type: suggestion.type || "preference",
            data: {
              [suggestion.key]: suggestion.value
            },
            description: suggestion.description || ""
          })
        });
        if (response.ok) {
          const data = await response.json();
          console.log("Memory committed:", data);
        }
      } catch (error) {
        console.error("Memory commit failed:", error);
      }
    };
    const handleVoiceInput = () => {
      if (!isVoiceMode) {
        if (!user?.id && !user?.user_id) {
          alert("\u0E01\u0E23\u0E38\u0E13\u0E32\u0E40\u0E02\u0E49\u0E32\u0E2A\u0E39\u0E48\u0E23\u0E30\u0E1A\u0E1A\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E43\u0E0A\u0E49\u0E42\u0E2B\u0E21\u0E14\u0E41\u0E0A\u0E17\u0E14\u0E49\u0E27\u0E22\u0E40\u0E2A\u0E35\u0E22\u0E07");
          return;
        }
        startVoiceMode();
      } else {
        stopVoiceMode();
      }
    };
    const startVoiceMode = () => {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognitionAPI) {
        alert("\u0E40\u0E1A\u0E23\u0E32\u0E27\u0E4C\u0E40\u0E0B\u0E2D\u0E23\u0E4C\u0E44\u0E21\u0E48\u0E23\u0E2D\u0E07\u0E23\u0E31\u0E1A\u0E01\u0E32\u0E23\u0E23\u0E31\u0E1A\u0E40\u0E2A\u0E35\u0E22\u0E07 (Speech Recognition) \u0E01\u0E23\u0E38\u0E13\u0E32\u0E43\u0E0A\u0E49 Chrome \u0E2B\u0E23\u0E37\u0E2D Edge");
        return;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {
        }
        recognitionRef.current = null;
      }
      const recognition = new SpeechRecognitionAPI();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "th-TH";
      recognition.onresult = (event) => {
        if (!isVoiceModeRef.current) return;
        const last = event.results.length - 1;
        const result = event.results[last];
        const transcript = result?.[0]?.transcript ?? "";
        const trimmed = transcript.trim();
        if (!trimmed) return;
        if (isMountedRef.current) {
          setVoiceDraft(trimmed);
        }
        if (result.isFinal) {
          try {
            recognition.stop();
          } catch (_) {
          }
          if (isMountedRef.current) {
            setIsRecording(false);
            setVoiceModeNotice("\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E01\u0E48\u0E2D\u0E19\u0E2A\u0E48\u0E07 \u0E2B\u0E23\u0E37\u0E2D\u0E01\u0E14\u0E1E\u0E39\u0E14\u0E43\u0E2B\u0E21\u0E48\u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07");
          }
        }
      };
      recognition.onend = () => {
        if (!isVoiceModeRef.current || !recognitionRef.current) return;
        if (synthesisRef.current || voiceAwaitingResponseRef.current || voiceAiSpeakingRef.current) return;
        try {
          recognitionRef.current.start();
          if (isMountedRef.current) setIsRecording(true);
        } catch (_) {
        }
      };
      recognition.onerror = (event) => {
        if (!isVoiceModeRef.current) return;
        if (event.error === "no-speech" || event.error === "aborted") return;
        if (isMountedRef.current) {
          setVoiceModeNotice(`\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E21\u0E35\u0E1B\u0E31\u0E0D\u0E2B\u0E32 (${event.error || "unknown"})`);
        }
      };
      recognitionRef.current = recognition;
      isVoiceModeRef.current = true;
      setIsVoiceMode(true);
      setIsRecording(true);
      setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
      try {
        recognition.start();
      } catch (e) {
        isVoiceModeRef.current = false;
        recognitionRef.current = null;
        setIsVoiceMode(false);
        setIsRecording(false);
        setVoiceModeNotice("\u0E40\u0E23\u0E34\u0E48\u0E21\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48");
      }
    };
    const stopVoiceMode = () => {
      isVoiceModeRef.current = false;
      voiceAwaitingResponseRef.current = false;
      voiceAiSpeakingRef.current = false;
      setVoiceDraft("");
      setIsVoiceMode(false);
      setIsRecording(false);
      setVoiceModeNotice("");
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {
        }
        recognitionRef.current = null;
      }
      if (synthesisRef.current) {
        if (typeof synthesisRef.current.pause === "function") {
          try {
            synthesisRef.current.pause();
          } catch (_) {
          }
        }
        try {
          window.speechSynthesis.cancel();
        } catch (_) {
        }
        synthesisRef.current = null;
      }
    };
    const speakText = async (text) => {
      if (!isVoiceModeRef.current) return;
      if (synthesisRef.current) {
        synthesisRef.current.pause();
        synthesisRef.current = null;
      }
      try {
        voiceAwaitingResponseRef.current = false;
        voiceAiSpeakingRef.current = true;
        if (recognitionRef.current) {
          try {
            recognitionRef.current.stop();
          } catch (_) {
          }
        }
        if (isMountedRef.current) {
          setIsRecording(false);
          setVoiceModeNotice("AI \u0E01\u0E33\u0E25\u0E31\u0E07\u0E15\u0E2D\u0E1A\u0E01\u0E25\u0E31\u0E1A\u0E14\u0E49\u0E27\u0E22\u0E40\u0E2A\u0E35\u0E22\u0E07...");
        }
        const response = await fetch(`${API_BASE_URL}/api/chat/tts`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            text,
            voice_name: "Kore",
            // ใช้เสียง Kore จาก Gemini
            audio_format: "MP3"
          })
        });
        if (!response.ok) {
          throw new Error(`TTS API error: ${response.status}`);
        }
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        synthesisRef.current = audio;
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          synthesisRef.current = null;
          voiceAiSpeakingRef.current = false;
          if (isVoiceModeRef.current && recognitionRef.current) {
            setIsRecording(true);
            setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
            try {
              recognitionRef.current.start();
            } catch (e) {
              console.log("Recognition already running or error:", e);
            }
          }
        };
        audio.onerror = (e) => {
          console.error("Audio playback error:", e);
          URL.revokeObjectURL(audioUrl);
          synthesisRef.current = null;
          voiceAiSpeakingRef.current = false;
          if (isVoiceModeRef.current && recognitionRef.current) {
            setIsRecording(true);
            setVoiceModeNotice("\u0E40\u0E25\u0E48\u0E19\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E15\u0E2D\u0E1A\u0E01\u0E25\u0E31\u0E1A\u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08 \u0E41\u0E15\u0E48\u0E22\u0E31\u0E07\u0E1F\u0E31\u0E07\u0E15\u0E48\u0E2D\u0E44\u0E14\u0E49");
            try {
              recognitionRef.current.start();
            } catch (e2) {
              console.log("Recognition start error:", e2);
            }
          }
        };
        setIsRecording(false);
        await audio.play();
      } catch (error) {
        console.error("Error generating or playing TTS:", error);
        voiceAwaitingResponseRef.current = false;
        voiceAiSpeakingRef.current = true;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "th-TH";
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.volume = 1;
        const voices = window.speechSynthesis.getVoices();
        const thaiVoice = voices.find(
          (voice) => voice.lang.includes("th") || voice.lang.includes("TH")
        );
        if (thaiVoice) {
          utterance.voice = thaiVoice;
        }
        synthesisRef.current = utterance;
        utterance.onend = () => {
          synthesisRef.current = null;
          voiceAiSpeakingRef.current = false;
          if (isVoiceModeRef.current && recognitionRef.current) {
            setIsRecording(true);
            setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
            try {
              recognitionRef.current.start();
            } catch (e) {
              console.log("Recognition start error:", e);
            }
          }
        };
        utterance.onerror = (e) => {
          console.error("Speech synthesis error:", e);
          synthesisRef.current = null;
          voiceAiSpeakingRef.current = false;
          if (isVoiceModeRef.current && recognitionRef.current) {
            setIsRecording(true);
            setVoiceModeNotice("\u0E40\u0E25\u0E48\u0E19\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E15\u0E2D\u0E1A\u0E01\u0E25\u0E31\u0E1A\u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08 \u0E41\u0E15\u0E48\u0E22\u0E31\u0E07\u0E1F\u0E31\u0E07\u0E15\u0E48\u0E2D\u0E44\u0E14\u0E49");
            try {
              recognitionRef.current.start();
            } catch (e2) {
              console.log("Recognition start error:", e2);
            }
          }
        };
        window.speechSynthesis.speak(utterance);
        setIsRecording(false);
      }
    };
    const handleSelectSlotChoice = async (choiceId, slotType, slotChoice, message) => {
      if (message?.id != null) {
        if (slotType === "flight") {
          setMessageIdsWithFlightSelected((prev) => /* @__PURE__ */ new Set([...prev, message.id]));
          const isOutbound = slotChoice?.flight_direction === "outbound" || slotChoice?.flight?.segments?.[0]?.direction && String(slotChoice.flight.segments[0].direction).includes("\u0E02\u0E32\u0E44\u0E1B");
          if (isOutbound) setMessageIdsWithOutboundSelected((prev) => /* @__PURE__ */ new Set([...prev, message.id]));
        }
        if (slotType === "hotel") setMessageIdsWithHotelSelected((prev) => /* @__PURE__ */ new Set([...prev, message.id]));
      }
      if (isConnected === false) {
        alert('\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E01\u0E31\u0E1A\u0E40\u0E0B\u0E34\u0E23\u0E4C\u0E1F\u0E40\u0E27\u0E2D\u0E23\u0E4C \u0E01\u0E23\u0E38\u0E13\u0E32\u0E01\u0E14 "\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48" \u0E17\u0E35\u0E48\u0E41\u0E16\u0E1A\u0E41\u0E08\u0E49\u0E07\u0E40\u0E15\u0E37\u0E2D\u0E19\u0E2B\u0E23\u0E37\u0E2D\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E27\u0E48\u0E32 Backend \u0E23\u0E31\u0E19\u0E2D\u0E22\u0E39\u0E48');
        return;
      }
      const tripId = activeTrip?.tripId;
      const targetId = activeTrip?.chatId || activeTrip?.tripId;
      if (!tripId || !targetId) return;
      const slotName = slotType === "flight" ? "\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19" : slotType === "hotel" ? "\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01" : slotType === "car" ? "\u0E23\u0E16" : "\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07";
      const userMessage = {
        id: Date.now(),
        type: "user",
        text: `\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${choiceId}`
        // ใช้คำว่า "เลือกช้อยส์" แทน "เลือก..."
      };
      appendMessageToTrip(targetId, userMessage);
      setProcessingTripId(targetId);
      try {
        const currentPlan = selectedPlan;
        if (!currentPlan) {
          const chatId = activeTrip?.chatId || tripId;
          const res = await fetch(`${API_BASE_URL}/api/chat/select_choice`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Conversation-ID": chatId
              // ✅ ส่ง chat_id ใน header
            },
            credentials: "include",
            body: JSON.stringify({
              user_id: userId,
              choice_id: choiceId,
              trip_id: tripId,
              // ✅ trip_id: สำหรับ 1 ทริป
              chat_id: chatId,
              // ✅ chat_id: สำหรับแต่ละแชท
              client_trip_id: tripId,
              // ✅ เก็บไว้สำหรับ backward compatibility
              choice_data: slotChoice || null,
              // ✅ ส่งข้อมูล choice ทั้งหมด
              slot_type: slotType || null
              // ✅ ส่ง slot type ด้วย
            })
          });
          if (!res.ok) {
            await sendMessage(`\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${choiceId}`);
            return;
          }
          const data = await res.json();
          const agentState2 = data.agent_state || {};
          const slotWorkflow = agentState2.slot_workflow || {};
          const currentSlot = slotWorkflow.current_slot;
          const isSlotWorkflowComplete = currentSlot === "summary" || agentState2.step === "trip_summary" || !currentSlot && !data.slot_choices && !data.slot_intent;
          const botMessage = {
            id: Date.now() + 1,
            type: "bot",
            text: toMessageText(data.response),
            debug: data.debug || null,
            travelSlots: data.travel_slots || null,
            searchResults: data.search_results || {},
            planChoices: data.plan_choices || [],
            agentState: data.agent_state || null,
            suggestions: data.suggestions || [],
            currentPlan: data.current_plan || null,
            tripTitle: data.trip_title || null,
            slotIntent: data.slot_intent || null,
            slotChoices: data.slot_choices || []
          };
          appendMessageToTrip(targetId, botMessage);
          if (data.plan_choices) setLatestPlanChoices(data.plan_choices);
          const hasOnlyTransferPending = data.slot_intent === "transfer" || data.slot_intent === "transport";
          const shouldShowSummary = isSlotWorkflowComplete || hasOnlyTransferPending;
          if (data.current_plan && shouldShowSummary) {
            setSelectedPlan(data.current_plan);
            setSelectedTravelSlots(data.travel_slots || null);
          } else if (data.current_plan) {
            setSelectedPlan(data.current_plan);
            setSelectedTravelSlots(data.travel_slots || null);
          } else {
            setSelectedPlan(null);
            setSelectedTravelSlots(null);
          }
          if (data.trip_title) setTripTitle(tripId, data.trip_title);
          return;
        }
        const updatedPlan = { ...currentPlan };
        const agentState = message?.agentState;
        const targetSegments = agentState?.target_segments;
        if (slotType === "hotel" && targetSegments && Array.isArray(targetSegments) && targetSegments.length > 0) {
          const hotelSegments = [...updatedPlan.hotel?.segments || []];
          const chosenHotel = slotChoice.hotel;
          targetSegments.forEach((segIdx) => {
            if (segIdx >= 0 && segIdx < hotelSegments.length) {
              const originalSeg = hotelSegments[segIdx];
              hotelSegments[segIdx] = {
                ...chosenHotel,
                // Keep segment-specific info
                nights: originalSeg.nights || chosenHotel.nights,
                cityCode: originalSeg.cityCode || chosenHotel.cityCode
              };
            }
          });
          const newPrice = hotelSegments.reduce((sum, seg) => {
            return sum + (seg.price_total || seg.price || 0);
          }, 0);
          updatedPlan.hotel = {
            ...updatedPlan.hotel,
            segments: hotelSegments,
            price_total: newPrice
          };
          const fp = updatedPlan.flight && (updatedPlan.flight.total_price != null || updatedPlan.flight.price_total != null) ? Number(updatedPlan.flight.total_price ?? updatedPlan.flight.price_total) : 0;
          const tp = updatedPlan.transport && (updatedPlan.transport.price != null || updatedPlan.transport.price_amount != null) ? Number(updatedPlan.transport.price ?? updatedPlan.transport.price_amount) : 0;
          updatedPlan.total_price = fp + newPrice + tp;
          setSelectedPlan(updatedPlan);
          const segmentNums = targetSegments.map((i) => i + 1).join(", ");
          await sendMessage(`\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01 ${choiceId} \u0E2A\u0E33\u0E2B\u0E23\u0E31\u0E1A segment ${segmentNums}`);
          return;
        }
        if (slotType === "flight" && targetSegments && Array.isArray(targetSegments) && targetSegments.length > 0) {
          const flightSegments = [...updatedPlan.flight?.segments || []];
          const chosenFlight = slotChoice.flight;
          const chosenSegments = chosenFlight.segments || [];
          for (let i = 0; i < targetSegments.length; i++) {
            const segIdx = targetSegments[i];
            if (segIdx >= 0 && segIdx < flightSegments.length) {
              const originalSeg = flightSegments[segIdx];
              const newSeg = chosenSegments[i] || chosenSegments[0];
              if (segIdx > 0) {
                const prevSeg = flightSegments[segIdx - 1];
                if (prevSeg.to !== newSeg.from) {
                  alert(`\u26A0\uFE0F Segment ${segIdx + 1} \u0E44\u0E21\u0E48\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E01\u0E31\u0E1A segment ${segIdx}
${prevSeg.to} \u2192 ${newSeg.from}`);
                  setIsTyping(false);
                  return;
                }
              }
              if (segIdx < flightSegments.length - 1) {
                const nextSeg = flightSegments[segIdx + 1];
                if (newSeg.to !== nextSeg.from) {
                  alert(`\u26A0\uFE0F Segment ${segIdx + 1} \u0E44\u0E21\u0E48\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E01\u0E31\u0E1A segment ${segIdx + 2}
${newSeg.to} \u2192 ${nextSeg.from}`);
                  setIsTyping(false);
                  return;
                }
              }
              flightSegments[segIdx] = newSeg;
            }
          }
          const newPrice = chosenFlight.total_price || flightSegments.reduce((sum, seg) => sum + (seg.price || 0), 0);
          const totalDuration = flightSegments.reduce((sum, seg) => {
            return sum + (seg.duration_sec || 0);
          }, 0);
          updatedPlan.flight = {
            ...updatedPlan.flight,
            segments: flightSegments,
            total_price: newPrice,
            total_duration_sec: totalDuration,
            // Update other flight metadata
            is_non_stop: flightSegments.length === 1,
            num_stops: flightSegments.length - 1
          };
          const hp = updatedPlan.hotel && (updatedPlan.hotel.total_price != null || updatedPlan.hotel.price_total != null) ? Number(updatedPlan.hotel.total_price ?? updatedPlan.hotel.price_total) : 0;
          const tp = updatedPlan.transport && (updatedPlan.transport.price != null || updatedPlan.transport.price_amount != null) ? Number(updatedPlan.transport.price ?? updatedPlan.transport.price_amount) : 0;
          updatedPlan.total_price = newPrice + hp + tp;
          setSelectedPlan(updatedPlan);
          const segmentNums = targetSegments.map((i) => i + 1).join(", ");
          await sendMessage(`\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${choiceId} \u0E2A\u0E33\u0E2B\u0E23\u0E31\u0E1A segment ${segmentNums}`);
          return;
        }
        if (slotType === "flight" && slotChoice?.flight) {
          updatedPlan.flight = slotChoice.flight;
        } else if (slotType === "hotel" && slotChoice?.hotel) {
          updatedPlan.hotel = slotChoice.hotel;
        } else if (slotType === "transport" && slotChoice?.transport) {
          updatedPlan.transport = slotChoice.transport;
        }
        const flightPrice = updatedPlan.flight && (updatedPlan.flight.total_price != null || updatedPlan.flight.price_total != null) ? Number(updatedPlan.flight.total_price ?? updatedPlan.flight.price_total) : 0;
        const hotelPrice = updatedPlan.hotel && (updatedPlan.hotel.total_price != null || updatedPlan.hotel.price_total != null) ? Number(updatedPlan.hotel.total_price ?? updatedPlan.hotel.price_total) : 0;
        const transportPrice = updatedPlan.transport && (updatedPlan.transport.price != null || updatedPlan.transport.price_amount != null) ? Number(updatedPlan.transport.price ?? updatedPlan.transport.price_amount) : 0;
        updatedPlan.total_price = flightPrice + hotelPrice + transportPrice;
        setSelectedPlan(updatedPlan);
        await sendMessage(`\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${choiceId}`);
      } catch (error) {
        console.error("Error selecting slot choice:", error);
      } finally {
        setProcessingTripId(null);
      }
    };
    const handleSelectPlanChoice = async (choiceId, choice = null) => {
      if (isConnected === false) {
        alert("Backend is not connected. Please start the backend server first.");
        return;
      }
      const tripId = activeTrip?.tripId;
      const targetId = activeTrip?.chatId || activeTrip?.tripId;
      if (!tripId || !targetId) return;
      let choiceData = choice;
      if (!choiceData) {
        const latestBotMessage2 = [...activeTrip?.messages || []].slice().reverse().find((m) => m.type === "bot" && m.planChoices && m.planChoices.length > 0);
        if (latestBotMessage2?.planChoices) {
          choiceData = latestBotMessage2.planChoices.find((c) => {
            const cId = typeof c.id === "number" ? c.id : typeof c.get === "function" ? c.get("id") : c.id;
            return parseInt(cId) === parseInt(choiceId);
          });
        }
      }
      const userMessage = {
        id: Date.now(),
        type: "user",
        text: `\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${choiceId}`
      };
      appendMessageToTrip(targetId, userMessage);
      setProcessingTripId(targetId);
      try {
        const res = await fetch(`${API_BASE_URL}/api/chat/select_choice`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            user_id: userId,
            choice_id: choiceId,
            trip_id: tripId,
            choice_data: choiceData || null
            // ✅ ส่งข้อมูล choice ทั้งหมด
          })
        });
        if (!res.ok) {
          setProcessingTripId(null);
          sendMessage(`\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${choiceId}`);
          return;
        }
        const data = await res.json();
        console.log("\u{1F4E5} select_choice response:", {
          hasCurrentPlan: !!data.current_plan,
          currentPlanKeys: data.current_plan ? Object.keys(data.current_plan) : [],
          agentState: data.agent_state,
          planChoicesCount: data.plan_choices?.length || 0,
          planChoices: data.plan_choices,
          response: data.response,
          choiceId
        });
        if (!data.plan_choices || data.plan_choices.length === 0) {
          console.warn("\u26A0\uFE0F No plan_choices in response, checking latest message...");
          const latestBotMessage2 = [...activeTrip?.messages || []].slice().reverse().find((m) => m.type === "bot" && m.planChoices && m.planChoices.length > 0);
          if (latestBotMessage2?.planChoices) {
            console.log("\u2705 Found plan_choices in latest message:", latestBotMessage2.planChoices.length);
            data.plan_choices = latestBotMessage2.planChoices;
            const foundChoice = latestBotMessage2.planChoices.find((p) => {
              const pId = typeof p.id === "number" ? p.id : typeof p.get === "function" ? p.get("id") : p.id;
              return parseInt(pId) === parseInt(choiceId);
            });
            if (foundChoice && !data.current_plan) {
              console.log("\u2705 Found choice in latest message, using as current_plan");
              data.current_plan = foundChoice;
            }
          }
        }
        if (!data.current_plan && data.plan_choices && data.plan_choices.length > 0) {
          const foundChoice = data.plan_choices.find((p) => {
            const pId = typeof p.id === "number" ? p.id : typeof p.get === "function" ? p.get("id") : p.id;
            return parseInt(pId) === parseInt(choiceId);
          });
          if (foundChoice) {
            console.log("\u2705 Found choice in plan_choices, using as current_plan");
            data.current_plan = foundChoice;
          }
        }
        const botMessage = {
          id: Date.now() + 1,
          type: "bot",
          text: toMessageText(data.response),
          debug: data.debug || null,
          travelSlots: data.travel_slots || null,
          searchResults: data.search_results || {},
          planChoices: data.plan_choices || [],
          agentState: data.agent_state || null,
          suggestions: data.suggestions || [],
          currentPlan: data.current_plan || null,
          tripTitle: data.trip_title || null
        };
        appendMessageToTrip(targetId, botMessage);
        if (data.plan_choices) setLatestPlanChoices(data.plan_choices);
        const agentState = data.agent_state || {};
        const slotWorkflow = agentState.slot_workflow || {};
        const currentSlot = slotWorkflow.current_slot;
        const isSlotWorkflowComplete = currentSlot === "summary" || agentState.step === "trip_summary" || !currentSlot && !data.slot_choices && !data.slot_intent;
        const hasOnlyTransferPending = data.slot_intent === "transfer" || data.slot_intent === "transport";
        const shouldShowSummary = isSlotWorkflowComplete || hasOnlyTransferPending;
        const isAgentMode = data.agent_state?.agent_mode || chatMode === "agent";
        if (data.current_plan) {
          if (isAgentMode || shouldShowSummary) {
            setSelectedPlan(data.current_plan);
            setSelectedTravelSlots(data.travel_slots || null);
            if (data.agent_state) {
              setLatestBotMessage((prev) => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
            }
            console.log("\u2705 Plan selected (Agent Mode or core ready):", {
              choiceId,
              isAgentMode,
              hasCurrentPlan: !!data.current_plan,
              agentState: data.agent_state,
              travelSlots: !!data.travel_slots
            });
          } else {
            setSelectedPlan(data.current_plan);
            setSelectedTravelSlots(data.travel_slots || null);
            if (data.agent_state) {
              setLatestBotMessage((prev) => prev ? { ...prev, agentState: data.agent_state } : { agentState: data.agent_state });
            }
            console.log("\u2705 Plan set (workflow in progress):", {
              choiceId,
              currentSlot,
              slotIntent: data.slot_intent
            });
          }
        } else {
          setSelectedPlan(null);
          setSelectedTravelSlots(null);
          console.warn("\u26A0\uFE0F No current_plan:", {
            hasCurrentPlan: !!data.current_plan,
            currentSlot,
            isSlotWorkflowComplete
          });
        }
        if (data.trip_title) {
          setTripTitle(tripId, data.trip_title);
        }
      } catch (e) {
        console.error("select_choice error:", e);
        sendMessage(`\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C ${choiceId}`);
      } finally {
        setProcessingTripId(null);
      }
    };
    const handleSuggestionClick = (suggestionText) => {
      sendMessage(suggestionText);
    };
    const showAgentEvaluationSwal = (accuracyScore, chatId) => {
      const uid = Date.now();
      const starContainerId = `agent-star-rating-${uid}`;
      const starValueId = `agent-star-value-${uid}`;
      return import_sweetalert2.default.fire({
        icon: "info",
        title: "\u0E04\u0E38\u0E13\u0E1E\u0E36\u0E07\u0E1E\u0E2D\u0E43\u0E08\u0E41\u0E04\u0E48\u0E44\u0E2B\u0E19",
        html: `
        <div style="text-align: left;">
          <p style="margin-bottom: 8px;">\u0E43\u0E2B\u0E49\u0E04\u0E30\u0E41\u0E19\u0E19 AI (\u0E14\u0E32\u0E27):</p>
          <div id="${starContainerId}" style="font-size: 32px; letter-spacing: 6px; margin: 12px 0; cursor: pointer; user-select: none;">
            <span class="agent-star" data-rating="1" style="color:#ddd">\u2605</span>
            <span class="agent-star" data-rating="2" style="color:#ddd">\u2605</span>
            <span class="agent-star" data-rating="3" style="color:#ddd">\u2605</span>
            <span class="agent-star" data-rating="4" style="color:#ddd">\u2605</span>
            <span class="agent-star" data-rating="5" style="color:#ddd">\u2605</span>
          </div>
          <input type="hidden" id="${starValueId}" value="0" />
        </div>
      `,
        confirmButtonText: "\u0E2A\u0E48\u0E07\u0E04\u0E30\u0E41\u0E19\u0E19",
        showCancelButton: true,
        cancelButtonText: "\u0E02\u0E49\u0E32\u0E21",
        confirmButtonColor: "#2563eb",
        cancelButtonColor: "#6b7280",
        allowOutsideClick: true,
        didOpen: () => {
          const container = document.getElementById(starContainerId);
          const input = document.getElementById(starValueId);
          if (!container || !input) return;
          const stars = container.querySelectorAll(".agent-star");
          const setStars = (n) => {
            input.value = n;
            stars.forEach((el) => {
              const r = parseInt(el.getAttribute("data-rating"), 10);
              el.style.color = r <= n ? "#f59e0b" : "#ddd";
            });
          };
          stars.forEach((el) => {
            el.addEventListener("click", () => setStars(parseInt(el.getAttribute("data-rating"), 10)));
          });
        },
        preConfirm: () => {
          const v = parseInt(document.getElementById(starValueId)?.value || "0", 10);
          if (v < 1 || v > 5) {
            import_sweetalert2.default.showValidationMessage("\u0E01\u0E23\u0E38\u0E13\u0E32\u0E43\u0E2B\u0E49\u0E14\u0E32\u0E27 1\u20135 \u0E01\u0E48\u0E2D\u0E19\u0E2A\u0E48\u0E07\u0E04\u0E30\u0E41\u0E19\u0E19");
            return false;
          }
          return v;
        }
      }).then((evalResult) => {
        if (evalResult?.value && typeof evalResult.value === "number" && evalResult.value >= 1 && evalResult.value <= 5) {
          const stars = evalResult.value;
          const mode = chatMode === "agent" ? "agent" : "ask";
          return fetch(`${API_BASE_URL}/api/chat/agent-feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ chat_id: chatId, stars, mode })
          }).then((res) => res.json()).then((data) => {
            if (data?.ok) import_sweetalert2.default.fire({ icon: "success", title: "\u0E02\u0E2D\u0E1A\u0E04\u0E38\u0E13\u0E04\u0E48\u0E30", text: "\u0E04\u0E30\u0E41\u0E19\u0E19\u0E02\u0E2D\u0E07\u0E17\u0E48\u0E32\u0E19\u0E08\u0E30\u0E16\u0E39\u0E01\u0E19\u0E33\u0E44\u0E1B\u0E1B\u0E23\u0E31\u0E1A\u0E1B\u0E23\u0E38\u0E07\u0E04\u0E27\u0E32\u0E21\u0E41\u0E21\u0E48\u0E19\u0E22\u0E33", timer: 2e3, showConfirmButton: false });
            return evalResult;
          }).catch(() => evalResult);
        }
        return evalResult;
      });
    };
    const handleConfirmBooking = async () => {
      const tripId = activeTrip?.tripId;
      const chatId = activeTrip?.chatId || tripId;
      const targetId = activeTrip?.chatId || activeTrip?.tripId;
      if (!tripId) return;
      if (!selectedPlan) {
        alert("\u26A0\uFE0F \u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E17\u0E23\u0E34\u0E1B \u0E01\u0E23\u0E38\u0E13\u0E32\u0E23\u0E2D\u0E43\u0E2B\u0E49 Agent \u0E2A\u0E23\u0E49\u0E32\u0E07\u0E41\u0E1C\u0E19\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E43\u0E2B\u0E49\u0E40\u0E2A\u0E23\u0E47\u0E08\u0E01\u0E48\u0E2D\u0E19");
        return;
      }
      try {
        const plan = selectedPlan || {};
        const travelSlots = selectedTravelSlots || {};
        const origin = travelSlots.origin_city || travelSlots.origin || plan.flight?.outbound?.[0]?.from || plan.flight?.segments?.[0]?.from || "";
        const destination = travelSlots.destination_city || travelSlots.destination || plan.flight?.inbound?.[0]?.to || plan.flight?.segments?.[plan.flight?.segments?.length - 1]?.to || "";
        const isInternationalTrip = !(isLocationInThailand(origin) && isLocationInThailand(destination));
        const visaFreeRoute = isVisaFreeRoute(userProfile?.nationality, destination);
        const hasPassportInfo = !!(userProfile?.passport_no && userProfile?.passport_expiry && userProfile?.nationality);
        const hasVisaInfo = !!(userProfile?.visa_type || userProfile?.visa_number || Array.isArray(user?.visa_records) && user.visa_records.length > 0);
        if (isInternationalTrip && (!hasPassportInfo || !visaFreeRoute && !hasVisaInfo)) {
          const missingDocs = [
            !hasPassportInfo ? "Passport" : null,
            !visaFreeRoute && !hasVisaInfo ? "Visa" : null
          ].filter(Boolean).join(", ");
          await import_sweetalert2.default.fire({
            icon: "warning",
            title: "\u0E40\u0E2D\u0E01\u0E2A\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E44\u0E21\u0E48\u0E04\u0E23\u0E1A",
            text: `\u0E17\u0E23\u0E34\u0E1B\u0E15\u0E48\u0E32\u0E07\u0E1B\u0E23\u0E30\u0E40\u0E17\u0E28\u0E15\u0E49\u0E2D\u0E07\u0E21\u0E35\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25 ${missingDocs} \u0E01\u0E48\u0E2D\u0E19\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07`,
            confirmButtonText: "\u0E44\u0E1B\u0E41\u0E01\u0E49\u0E44\u0E02\u0E42\u0E1B\u0E23\u0E44\u0E1F\u0E25\u0E4C"
          });
          return;
        }
        if (isInternationalTrip && visaFreeRoute) {
          appendMessageToTrip(targetId, {
            id: Date.now() + 2,
            type: "bot",
            text: "\u2139\uFE0F \u0E40\u0E2A\u0E49\u0E19\u0E17\u0E32\u0E07\u0E19\u0E35\u0E49\u0E1F\u0E23\u0E35\u0E27\u0E35\u0E0B\u0E48\u0E32\u0E2A\u0E33\u0E2B\u0E23\u0E31\u0E1A\u0E2A\u0E31\u0E0D\u0E0A\u0E32\u0E15\u0E34\u0E02\u0E2D\u0E07\u0E04\u0E38\u0E13 \u0E43\u0E0A\u0E49 Passport \u0E17\u0E35\u0E48\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E2B\u0E21\u0E14\u0E2D\u0E32\u0E22\u0E38\u0E43\u0E19\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E44\u0E14\u0E49"
          });
        }
        setIsBooking(true);
        setBookingResult(null);
        setProcessingTripId(targetId);
        let totalPrice = 0;
        let currency = "THB";
        if (plan.total_price) {
          totalPrice = parseFloat(plan.total_price) || 0;
          currency = plan.currency || "THB";
        } else {
          if (plan.flight?.total_price) {
            totalPrice += parseFloat(plan.flight.total_price) || 0;
            currency = plan.flight.currency || currency;
          }
          if (plan.hotel && (plan.hotel.total_price != null || plan.hotel.price_total != null)) {
            totalPrice += parseFloat(plan.hotel.total_price ?? plan.hotel.price_total) || 0;
            currency = plan.hotel.currency || currency;
          }
          if (plan.transport && (plan.transport.price != null || plan.transport.price_amount != null)) {
            totalPrice += parseFloat(plan.transport.price ?? plan.transport.price_amount) || 0;
            currency = plan.transport.currency || currency;
          }
        }
        const bookingTravelSlots = {
          // ✅ ใช้ segments จาก travelSlots ถ้ามี (backend format)
          flights: travelSlots.flights || plan.flight?.segments || plan.flight?.outbound || [],
          accommodations: travelSlots.accommodations || plan.hotel?.segments || [],
          ground_transport: travelSlots.ground_transport || plan.transport?.segments || [],
          // ✅ เพิ่มข้อมูลพื้นฐาน
          origin_city: travelSlots.origin_city || travelSlots.origin || plan.flight?.outbound?.[0]?.from || plan.flight?.segments?.[0]?.from,
          destination_city: travelSlots.destination_city || travelSlots.destination || plan.flight?.inbound?.[0]?.to || plan.flight?.segments?.[plan.flight?.segments?.length - 1]?.to,
          departure_date: travelSlots.departure_date || travelSlots.start_date,
          return_date: travelSlots.return_date || travelSlots.end_date,
          adults: travelSlots.adults || travelSlots.guests || 1,
          children: travelSlots.children ?? travelSlots.children_2_11 ?? 0,
          infants: travelSlots.infants ?? (travelSlots.infants_with_seat ?? 0) + (travelSlots.infants_on_lap ?? 0),
          children_2_11: travelSlots.children_2_11 ?? travelSlots.children ?? 0,
          infants_with_seat: travelSlots.infants_with_seat ?? 0,
          infants_on_lap: travelSlots.infants_on_lap ?? 0,
          nights: travelSlots.nights
        };
        if (!plan || typeof plan !== "object" || Object.keys(plan).length === 0) {
          alert("\u26A0\uFE0F \u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E17\u0E23\u0E34\u0E1B\u0E44\u0E21\u0E48\u0E04\u0E23\u0E1A\u0E16\u0E49\u0E27\u0E19 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E23\u0E2D\u0E43\u0E2B\u0E49 Agent \u0E2A\u0E23\u0E49\u0E32\u0E07\u0E41\u0E1C\u0E19\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07\u0E43\u0E2B\u0E49\u0E40\u0E2A\u0E23\u0E47\u0E08\u0E01\u0E48\u0E2D\u0E19");
          setIsBooking(false);
          return;
        }
        if (!userId) {
          alert("\u26A0\uFE0F \u0E44\u0E21\u0E48\u0E1E\u0E1A\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1C\u0E39\u0E49\u0E43\u0E0A\u0E49 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E40\u0E02\u0E49\u0E32\u0E2A\u0E39\u0E48\u0E23\u0E30\u0E1A\u0E1A\u0E43\u0E2B\u0E21\u0E48");
          setIsBooking(false);
          return;
        }
        if (isNaN(totalPrice) || totalPrice < 0) {
          console.warn("\u26A0\uFE0F Invalid total_price, using 0:", totalPrice);
          totalPrice = 0;
        }
        const bookingPayload = {
          trip_id: tripId,
          chat_id: chatId,
          user_id: userId,
          plan,
          travel_slots: bookingTravelSlots,
          total_price: totalPrice,
          currency: currency || "THB",
          mode: chatMode || "normal",
          auto_booked: false
        };
        if (editReplaceBookingId) {
          bookingPayload.replace_booking_id = editReplaceBookingId;
        }
        console.log("\u{1F4E4} Sending booking request:", {
          trip_id: bookingPayload.trip_id,
          chat_id: bookingPayload.chat_id,
          user_id: bookingPayload.user_id,
          has_plan: !!bookingPayload.plan,
          plan_keys: bookingPayload.plan ? Object.keys(bookingPayload.plan) : [],
          has_travel_slots: !!bookingPayload.travel_slots,
          travel_slots_keys: bookingPayload.travel_slots ? Object.keys(bookingPayload.travel_slots) : [],
          total_price: bookingPayload.total_price,
          currency: bookingPayload.currency,
          mode: bookingPayload.mode
        });
        const headers = { "Content-Type": "application/json" };
        const uid = user?.user_id || user?.id;
        if (uid) headers["X-User-ID"] = uid;
        const res = await fetch(`${API_BASE_URL}/api/booking/create`, {
          method: "POST",
          headers,
          credentials: "include",
          body: JSON.stringify(bookingPayload)
        });
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          let errorMsg = "Booking failed";
          if (data) {
            if (data.detail) {
              if (Array.isArray(data.detail)) {
                errorMsg = data.detail.map((err) => `${err.loc?.join(".")}: ${err.msg}`).join(", ");
              } else if (typeof data.detail === "string") {
                errorMsg = data.detail;
              } else if (data.detail.message) {
                errorMsg = data.detail.message;
              } else {
                errorMsg = JSON.stringify(data.detail);
              }
            } else if (data.message) {
              errorMsg = data.message;
            }
          }
          console.error("\u274C Booking error:", {
            status: res.status,
            statusText: res.statusText,
            data
          });
          const isAlreadyBooked = typeof errorMsg === "string" && /already exists|booking for this trip already/i.test(errorMsg);
          const result2 = isAlreadyBooked ? {
            ok: false,
            already_booked: true,
            message: '\u0E17\u0E23\u0E34\u0E1B\u0E19\u0E35\u0E49\u0E08\u0E2D\u0E07\u0E44\u0E1B\u0E41\u0E25\u0E49\u0E27 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E41\u0E01\u0E49\u0E44\u0E02\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E40\u0E14\u0E34\u0E21\u0E17\u0E35\u0E48 "My Bookings"',
            detail: errorMsg
          } : {
            ok: false,
            message: `\u274C \u0E2A\u0E23\u0E49\u0E32\u0E07\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08: ${errorMsg}`,
            detail: data?.detail || errorMsg
          };
          setBookingResult(result2);
          updateMessageBookingResult(targetId, result2);
          if (isAlreadyBooked) setExistingBookingForTripId(targetId);
          appendMessageToTrip(targetId, {
            id: Date.now() + 1,
            type: "bot",
            text: toMessageText(result2.message)
          });
          if (isAlreadyBooked) {
            import_sweetalert2.default.fire({
              icon: "info",
              title: "\u0E08\u0E2D\u0E07\u0E44\u0E1B\u0E41\u0E25\u0E49\u0E27",
              html: "<p>\u0E17\u0E23\u0E34\u0E1B\u0E19\u0E35\u0E49\u0E21\u0E35\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E2D\u0E22\u0E39\u0E48\u0E41\u0E25\u0E49\u0E27 \u0E01\u0E23\u0E38\u0E13\u0E32\u0E41\u0E01\u0E49\u0E44\u0E02\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E40\u0E14\u0E34\u0E21\u0E17\u0E35\u0E48 <strong>My Bookings</strong></p>",
              confirmButtonText: "\u0E44\u0E1B\u0E17\u0E35\u0E48 My Bookings",
              showCancelButton: true,
              cancelButtonText: "\u0E1B\u0E34\u0E14",
              confirmButtonColor: "#2563eb",
              cancelButtonColor: "#6b7280"
            }).then((r) => {
              if (r.isConfirmed && onNavigateToBookings) onNavigateToBookings();
            });
          }
          return;
        }
        const result = {
          ok: true,
          message: data?.message || "\u2705 \u0E2A\u0E23\u0E49\u0E32\u0E07\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08",
          booking_id: data?.booking_id || null,
          status: data?.status || "pending_payment",
          total_price: data?.total_price || 0,
          currency: data?.currency || "THB",
          needs_payment: true
        };
        setBookingResult(result);
        updateMessageBookingResult(targetId, result);
        setExistingBookingForTripId(targetId);
        const messageText = toMessageText(result.message);
        appendMessageToTrip(targetId, {
          id: Date.now() + 1,
          type: "bot",
          text: messageText + '\n\u0E01\u0E23\u0E38\u0E13\u0E32\u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\n\n\u{1F4CB} \u0E04\u0E38\u0E13\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E14\u0E39\u0E23\u0E32\u0E22\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E17\u0E35\u0E48 "My Bookings"',
          agentState: { intent: "booking", step: "pending_payment", steps: [] }
        });
        if (editReplaceBookingId) {
          setEditReplaceBookingId(null);
          setIsEditMode(false);
        }
        if (onRefreshNotifications) {
          onRefreshNotifications();
        }
        window.dispatchEvent(new Event("bookingCreated"));
        showAgentEvaluationSwal(null, chatId).then(() => {
          if (onNavigateToBookings) onNavigateToBookings();
        });
      } catch (error) {
        const result = {
          ok: false,
          message: `\u274C \u0E40\u0E01\u0E34\u0E14\u0E02\u0E49\u0E2D\u0E1C\u0E34\u0E14\u0E1E\u0E25\u0E32\u0E14: ${error.message || "Unknown error"}`,
          detail: error.message
        };
        setBookingResult(result);
      } finally {
        setIsBooking(false);
        setProcessingTripId(null);
      }
    };
    const handlePayment = async (bookingId) => {
      setIsBooking(true);
      setBookingResult(null);
      try {
        const res = await fetch(`${API_BASE_URL}/api/booking/payment?booking_id=${bookingId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include"
        });
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          const msg = data && (data.detail?.message || data.detail?.detail || data.detail || data.message) || "Payment failed";
          const errorMsg = typeof msg === "string" ? msg : JSON.stringify(msg);
          const result2 = {
            ok: false,
            message: `\u274C \u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08: ${errorMsg}`,
            detail: data?.detail || errorMsg
          };
          setBookingResult(result2);
          return;
        }
        if (data && data.payment_url) {
          window.location.href = data.payment_url;
          return;
        }
        const result = {
          ok: true,
          message: data?.message || "\u2705 \u0E0A\u0E33\u0E23\u0E30\u0E40\u0E07\u0E34\u0E19\u0E41\u0E25\u0E30\u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08",
          booking_reference: data?.booking_reference || null,
          status: data?.status || "confirmed",
          needs_payment: false
        };
        setBookingResult(result);
        const targetId = activeTrip?.chatId || activeTrip?.tripId;
        if (targetId) {
          const messageText = toMessageText(result.message);
          appendMessageToTrip(targetId, {
            id: Date.now() + 1,
            type: "bot",
            text: messageText + (result.booking_reference ? `
\u{1F4CB} \u0E2B\u0E21\u0E32\u0E22\u0E40\u0E25\u0E02\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07: ${result.booking_reference}` : "") + '\n\n\u{1F4CB} \u0E04\u0E38\u0E13\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E14\u0E39\u0E23\u0E32\u0E22\u0E01\u0E32\u0E23\u0E08\u0E2D\u0E07\u0E44\u0E14\u0E49\u0E17\u0E35\u0E48 "My Bookings"',
            agentState: { intent: "booking", step: "completed", steps: [] },
            currentPlan: selectedPlan || null,
            travelSlots: selectedTravelSlots || null,
            workflowValidation: { current_step: "completed", is_complete: true }
          });
        }
      } catch (error) {
        const result = {
          ok: false,
          message: `\u274C \u0E40\u0E01\u0E34\u0E14\u0E02\u0E49\u0E2D\u0E1C\u0E34\u0E14\u0E1E\u0E25\u0E32\u0E14: ${error.message || "Unknown error"}`,
          detail: error.message
        };
        setBookingResult(result);
      } finally {
        setIsBooking(false);
      }
    };
    const handleEditUserProfile = () => {
      alert("\u0E1F\u0E35\u0E40\u0E08\u0E2D\u0E23\u0E4C\u0E41\u0E01\u0E49\u0E44\u0E02\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E1C\u0E39\u0E49\u0E43\u0E0A\u0E49\u0E08\u0E30\u0E40\u0E1B\u0E34\u0E14\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19\u0E40\u0E23\u0E47\u0E27\u0E46 \u0E19\u0E35\u0E49");
    };
    const lastBotWithState = [...messages].slice().reverse().find((m) => m.type === "bot" && m.agentState);
    const currentAgentState = lastBotWithState?.agentState || null;
    const latestBotWithPlan = (0, import_react13.useMemo)(() => {
      if (selectedPlan) {
        const lastBotWithPlan = [...messages].slice().reverse().find((m) => m.type === "bot" && m.currentPlan && !m.text?.includes("\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E21\u0E35\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C"));
        if (lastBotWithPlan) {
          return {
            ...lastBotWithPlan,
            currentPlan: selectedPlan,
            travelSlots: selectedTravelSlots || lastBotWithPlan.travelSlots,
            agentState: lastBotWithPlan.agentState || { intent: "edit", step: "choice_selected", steps: [] }
          };
        }
        const lastBotMsg = [...messages].slice().reverse().find((m) => m.type === "bot");
        if (lastBotMsg) {
          return {
            ...lastBotMsg,
            currentPlan: selectedPlan,
            travelSlots: selectedTravelSlots || lastBotMsg.travelSlots,
            agentState: lastBotMsg.agentState || { intent: "edit", step: "choice_selected", steps: [] }
          };
        }
      }
      const choiceSelectedMsg = [...messages].slice().reverse().find(
        (m) => m.type === "bot" && m.currentPlan && m.agentState?.step === "choice_selected" && !m.text?.includes("\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E21\u0E35\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C")
      );
      if (choiceSelectedMsg) return choiceSelectedMsg;
      return [...messages].slice().reverse().find((m) => m.type === "bot" && m.currentPlan && !m.text?.includes("\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E21\u0E35\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C"));
    }, [messages, selectedPlan, selectedTravelSlots]);
    const effectiveSelectedPlan = selectedPlan || latestBotWithPlan?.currentPlan || null;
    const effectiveSelectedTravelSlots = selectedTravelSlots || latestBotWithPlan?.travelSlots || null;
    const latestBotWithChoices = (0, import_react13.useMemo)(() => {
      const msgs = activeTrip?.messages || [];
      return [...msgs].reverse().find(
        (m) => m.type === "bot" && (Array.isArray(m.planChoices) && m.planChoices.length > 0 || Array.isArray(m.slotChoices) && m.slotChoices.length > 0)
      ) || null;
    }, [activeTrip?.messages]);
    const userProfile = (0, import_react13.useMemo)(() => {
      if (!user) return null;
      const fullName = (user.name || "").trim();
      const parts = fullName.split(/\s+/).filter(Boolean);
      const first_name = (user.first_name || user.given_name || parts[0] || "").trim();
      const last_name = (user.last_name || user.family_name || parts.slice(1).join(" ") || "").trim();
      return {
        first_name,
        last_name,
        first_name_th: user.first_name_th || "",
        last_name_th: user.last_name_th || "",
        national_id: user.national_id || "",
        email: user.email || "",
        phone: user.phone || "",
        dob: user.dob || "",
        gender: user.gender || "",
        passport_no: user.passport_no || "",
        passport_expiry: user.passport_expiry || "",
        passport_issue_date: user.passport_issue_date || "",
        passport_issuing_country: user.passport_issuing_country || "",
        passport_given_names: user.passport_given_names || "",
        passport_surname: user.passport_surname || "",
        nationality: user.nationality || "",
        place_of_birth: user.place_of_birth || "",
        // ข้อมูลวีซ่า / โรงแรม / อื่นๆ จากโปรไฟล์
        ...user.visa_type && { visa_type: user.visa_type },
        ...user.visa_number && { visa_number: user.visa_number },
        ...user.visa_issue_date && { visa_issue_date: user.visa_issue_date },
        ...user.visa_expiry_date && { visa_expiry_date: user.visa_expiry_date },
        ...user.visa_issuing_country && { visa_issuing_country: user.visa_issuing_country },
        ...user.visa_entry_type && { visa_entry_type: user.visa_entry_type },
        ...user.visa_purpose && { visa_purpose: user.visa_purpose }
      };
    }, [user]);
    const getTypingText = () => {
      if (agentStatus && agentStatus.message) {
        return agentStatus.message;
      }
      if (!currentAgentState) return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E23\u0E34\u0E48\u0E21\u0E15\u0E49\u0E19...";
      const step = currentAgentState.step;
      const intent = currentAgentState.intent;
      if (step) {
        switch (step) {
          case "start":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E23\u0E34\u0E48\u0E21\u0E15\u0E49\u0E19...";
          case "planning":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E32\u0E07\u0E41\u0E1C\u0E19\u0E17\u0E23\u0E34\u0E1B...";
          case "trip_summary":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13...";
          case "choice_selected":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2D\u0E31\u0E1B\u0E40\u0E14\u0E15\u0E41\u0E1E\u0E25\u0E19...";
          case "no_previous_choices":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01...";
          default:
            if (currentAgentState.slot_workflow?.current_slot) {
              const slot = currentAgentState.slot_workflow.current_slot;
              if (slot === "summary") return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13...";
              if (slot === "flight") return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E08\u0E31\u0E14\u0E01\u0E32\u0E23\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19...";
              if (slot === "hotel") return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E08\u0E31\u0E14\u0E01\u0E32\u0E23\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01...";
              if (slot === "transfer" || slot === "transport") return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E08\u0E31\u0E14\u0E01\u0E32\u0E23\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07...";
            }
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E34\u0E14\u0E04\u0E33\u0E15\u0E2D\u0E1A\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13...";
        }
      }
      if (intent) {
        switch (intent) {
          case "collect_preferences":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E01\u0E47\u0E1A\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E2A\u0E44\u0E15\u0E25\u0E4C\u0E01\u0E32\u0E23\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E08\u0E32\u0E01\u0E04\u0E33\u0E15\u0E2D\u0E1A\u0E02\u0E2D\u0E07\u0E04\u0E38\u0E13...";
          case "suggest_destination":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E1B\u0E23\u0E35\u0E22\u0E1A\u0E40\u0E17\u0E35\u0E22\u0E1A\u0E08\u0E38\u0E14\u0E2B\u0E21\u0E32\u0E22\u0E17\u0E35\u0E48\u0E40\u0E02\u0E49\u0E32\u0E01\u0E31\u0E1A\u0E2A\u0E44\u0E15\u0E25\u0E4C\u0E02\u0E2D\u0E07\u0E04\u0E38\u0E13...";
          case "plan_trip_and_autoselect":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E32\u0E07\u0E41\u0E1E\u0E47\u0E01\u0E40\u0E01\u0E08\u0E17\u0E23\u0E34\u0E1B\u0E41\u0E25\u0E30\u0E04\u0E33\u0E19\u0E27\u0E13\u0E23\u0E32\u0E04\u0E32\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14...";
          case "edit_plan":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E1B\u0E23\u0E31\u0E1A\u0E41\u0E1E\u0E25\u0E19\u0E43\u0E2B\u0E49\u0E15\u0E23\u0E07\u0E43\u0E08\u0E21\u0E32\u0E01\u0E02\u0E36\u0E49\u0E19...";
          case "confirm_plan":
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E23\u0E38\u0E1B\u0E17\u0E23\u0E34\u0E1B\u0E09\u0E1A\u0E31\u0E1A\u0E2A\u0E38\u0E14\u0E17\u0E49\u0E32\u0E22\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13\u0E15\u0E23\u0E27\u0E08\u0E14\u0E39...";
          default:
            return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E34\u0E14\u0E04\u0E33\u0E15\u0E2D\u0E1A\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13...";
        }
      }
      return "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E34\u0E14\u0E04\u0E33\u0E15\u0E2D\u0E1A\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13...";
    };
    const getToolInfo = (step) => {
      const toolMap = {
        "search_flights": "\u{1F50D} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19...",
        "search_hotels": "\u{1F3E8} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01...",
        "search_transfers": "\u{1F697} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07...",
        "search_activities": "\u{1F3AF} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32\u0E01\u0E34\u0E08\u0E01\u0E23\u0E23\u0E21...",
        "geocode_location": "\u{1F4CD} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32\u0E15\u0E33\u0E41\u0E2B\u0E19\u0E48\u0E07...",
        "find_nearest_airport": "\u2708\uFE0F \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32\u0E2A\u0E19\u0E32\u0E21\u0E1A\u0E34\u0E19\u0E43\u0E01\u0E25\u0E49\u0E40\u0E04\u0E35\u0E22\u0E07...",
        "get_place_details": "\u{1F4CB} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E14\u0E36\u0E07\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E2A\u0E16\u0E32\u0E19\u0E17\u0E35\u0E48...",
        "thinking": "\u{1F914} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E34\u0E14...",
        "recall": "\u{1F9E0} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E23\u0E30\u0E25\u0E36\u0E01\u0E04\u0E27\u0E32\u0E21\u0E08\u0E33...",
        "processing": "\u2699\uFE0F \u0E01\u0E33\u0E25\u0E31\u0E07\u0E1B\u0E23\u0E30\u0E21\u0E27\u0E25\u0E1C\u0E25..."
      };
      if (step === "heartbeat") return null;
      return toolMap[step] || null;
    };
    const hashString = (input) => {
      const s = String(input || "");
      let h = 0;
      for (let i = 0; i < s.length; i += 1) {
        h = h * 31 + s.charCodeAt(i) >>> 0;
      }
      return h;
    };
    const getChoiceCardStyle = (choice, idx, totalChoices, scopeKey = "") => {
      if (!totalChoices || totalChoices <= 10 || idx < 10) return void 0;
      const stableId = `${scopeKey}|${choice?.id || choice?._original_id || choice?.title || idx}`;
      const h = hashString(stableId);
      const hueA = h % 360;
      const hueB = (hueA + 35 + h % 70) % 360;
      const satA = 62 + h % 12;
      const satB = 74 + h % 14;
      const lightA = 34 + h % 8;
      const lightB = 46 + h % 8;
      return {
        background: `linear-gradient(135deg, hsl(${hueA} ${satA}% ${lightA}%), hsl(${hueB} ${satB}% ${lightB}%))`
      };
    };
    const theme = useTheme();
    const { t } = useLanguage();
    const fontSize = useFontSize();
    return /* @__PURE__ */ import_react13.default.createElement(ChatErrorBoundary, null, /* @__PURE__ */ import_react13.default.createElement("div", { className: "chat-container", "data-theme": theme, "data-font-size": fontSize }, /* @__PURE__ */ import_react13.default.createElement(
      AppHeader,
      {
        activeTab: "ai",
        user,
        onNavigateToHome,
        onTabChange: (tab) => {
          if (tab === "flights" && onNavigateToFlights) {
            onNavigateToFlights();
          } else if (tab === "hotels" && onNavigateToHotels) {
            onNavigateToHotels();
          } else if (tab === "car-rentals" && onNavigateToCarRentals) {
            onNavigateToCarRentals();
          } else {
            setActiveTab(tab);
          }
        },
        onNavigateToBookings,
        onNavigateToAI: () => {
          const chatInput = document.querySelector(".chat-input-textarea");
          if (chatInput) {
            chatInput.focus();
          }
        },
        onLogout,
        onSignIn,
        onAIClick: () => {
          const chatInput = document.querySelector(".chat-input-textarea");
          if (chatInput) {
            chatInput.focus();
          }
        },
        isConnected,
        notificationCount,
        notifications,
        onNavigateToProfile,
        onNavigateToSettings,
        onMarkNotificationAsRead
      }
    ), /* @__PURE__ */ import_react13.default.createElement(
      "main",
      {
        className: `chat-main chat-main-split ${isSidebarOpen ? "sidebar-open" : "sidebar-closed"}`,
        "data-theme": theme,
        "data-font-size": fontSize,
        onTouchStart,
        onTouchMove,
        onTouchEnd
      },
      isSidebarOpen && /* @__PURE__ */ import_react13.default.createElement(
        "div",
        {
          className: "sidebar-overlay-mobile",
          onClick: () => setIsSidebarOpen(false)
        }
      ),
      /* @__PURE__ */ import_react13.default.createElement("aside", { className: `trip-sidebar ${isSidebarOpen ? "trip-sidebar-open" : "trip-sidebar-closed"}` }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-sidebar-header" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-sidebar-title" }, t("chat.tripHistory")), /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-sidebar-header-actions" }, /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          className: "trip-new-btn",
          onClick: handleNewTrip,
          title: isSidebarOpen ? t("chat.newTrip") : t("chat.newTrip")
        },
        isSidebarOpen ? t("chat.newTrip") : "+"
      ), /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          className: "trip-sidebar-toggle mobile-only",
          onClick: () => setIsSidebarOpen(!isSidebarOpen),
          title: isSidebarOpen ? "\u0E0B\u0E48\u0E2D\u0E19\u0E1B\u0E23\u0E30\u0E27\u0E31\u0E15\u0E34\u0E17\u0E23\u0E34\u0E1B" : "\u0E41\u0E2A\u0E14\u0E07\u0E1B\u0E23\u0E30\u0E27\u0E31\u0E15\u0E34\u0E17\u0E23\u0E34\u0E1B"
        },
        isSidebarOpen ? "\u25C0" : "\u25B6"
      ))), isSidebarOpen && /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-list" }, isLoadingSessions && /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-list-loading" }, [1, 2, 3].map((i) => /* @__PURE__ */ import_react13.default.createElement("div", { key: i, className: "trip-item-skeleton" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "skeleton-title" }), /* @__PURE__ */ import_react13.default.createElement("div", { className: "skeleton-sub" })))), !isLoadingSessions && sortedTrips.map((t2, idx) => {
        const isActive = (t2.chatId || t2.tripId) === (activeChat?.chatId || activeChat?.tripId || activeTripId);
        const isEditing = editingTripId === t2.tripId;
        const isProcessing = processingTripId === t2.tripId;
        const baseId = t2.chatId ?? t2.tripId;
        const uniqueKey = baseId != null ? `trip-${baseId}-${idx}` : `trip-idx-${idx}`;
        return /* @__PURE__ */ import_react13.default.createElement(
          "div",
          {
            key: uniqueKey,
            className: `trip-item ${isActive ? "trip-item-active" : ""} ${t2.pinned ? "trip-item-pinned" : ""}`,
            onClick: () => {
              if (!isEditing) {
                const id = t2.chatId || t2.tripId;
                setActiveTripId(id);
                loadHistoryForChat(id);
              } else {
                console.log("\u26A0\uFE0F Cannot switch while editing this trip");
              }
            },
            title: t2.title
          },
          /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-item-top" }, isEditing ? /* @__PURE__ */ import_react13.default.createElement(
            "input",
            {
              type: "text",
              value: editingTripName,
              onChange: (e) => setEditingTripName(e.target.value),
              onKeyPress: (e) => {
                if (e.key === "Enter") {
                  handleSaveTripName(t2.tripId);
                } else if (e.key === "Escape") {
                  handleCancelEditTripName();
                }
              },
              onBlur: () => handleSaveTripName(t2.tripId),
              className: "trip-edit-input",
              autoFocus: true,
              onClick: (e) => e.stopPropagation()
            }
          ) : /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-item-title-wrapper" }, t2.pinned && /* @__PURE__ */ import_react13.default.createElement("span", { className: "trip-pin-icon", title: "\u0E1B\u0E31\u0E01\u0E2B\u0E21\u0E38\u0E14" }, "\u{1F4CC}"), /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-item-title" }, t2.title || "\u0E17\u0E23\u0E34\u0E1B"), isProcessing && /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-spinner", title: "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E1B\u0E23\u0E30\u0E21\u0E27\u0E25\u0E1C\u0E25..." })), /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-item-actions" }, !isEditing && /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, /* @__PURE__ */ import_react13.default.createElement(
            "button",
            {
              className: "trip-edit-btn",
              onClick: (e) => {
                e.stopPropagation();
                handleEditTripName(t2.tripId, t2.title);
              },
              title: "\u0E41\u0E01\u0E49\u0E44\u0E02\u0E0A\u0E37\u0E48\u0E2D\u0E17\u0E23\u0E34\u0E1B"
            },
            "\u270F\uFE0F"
          ), /* @__PURE__ */ import_react13.default.createElement(
            "button",
            {
              className: `trip-pin-btn ${t2.pinned ? "trip-pin-btn-active" : ""}`,
              onClick: (e) => {
                e.stopPropagation();
                handleTogglePin(t2.tripId);
              },
              title: t2.pinned ? "\u0E22\u0E01\u0E40\u0E25\u0E34\u0E01\u0E1B\u0E31\u0E01\u0E2B\u0E21\u0E38\u0E14" : "\u0E1B\u0E31\u0E01\u0E2B\u0E21\u0E38\u0E14\u0E17\u0E23\u0E34\u0E1B"
            },
            "\u{1F4CC}"
          )), /* @__PURE__ */ import_react13.default.createElement(
            "button",
            {
              className: "trip-delete-btn",
              onClick: (e) => {
                e.stopPropagation();
                handleDeleteTrip(t2.tripId);
              },
              title: "\u0E25\u0E1A\u0E17\u0E23\u0E34\u0E1B"
            },
            "\u2715"
          ))),
          !isEditing && /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-item-sub" }, "\u0E2D\u0E31\u0E1B\u0E40\u0E14\u0E15: ", shortDate(t2.updatedAt))
        );
      })), /* @__PURE__ */ import_react13.default.createElement("div", { className: "trip-sidebar-footer" }))),
      /* @__PURE__ */ import_react13.default.createElement("div", { className: "chat-box" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "chatbox-header" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "chatbox-header-left" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "chatbox-avatar" }, /* @__PURE__ */ import_react13.default.createElement("svg", { className: "chatbox-icon", fill: "none", stroke: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react13.default.createElement("path", { strokeLinecap: "round", strokeLinejoin: "round", strokeWidth: 2, d: "M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" }))), /* @__PURE__ */ import_react13.default.createElement("div", null, /* @__PURE__ */ import_react13.default.createElement("h3", { className: "chatbox-title" }, activeTrip?.title || "AI Travel Assistant"))), /* @__PURE__ */ import_react13.default.createElement("div", { className: "chatbox-header-right" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "chat-mode-toggle", style: {
        display: "flex",
        alignItems: "center",
        gap: "8px",
        marginRight: "12px",
        padding: "4px",
        background: "rgba(255, 255, 255, 0.1)",
        borderRadius: "8px",
        fontSize: "13px"
      } }, isEditMode && /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, /* @__PURE__ */ import_react13.default.createElement("span", { style: { fontSize: "11px", color: "rgba(255,255,255,0.7)", marginRight: "4px" }, title: "\u0E42\u0E2B\u0E21\u0E14\u0E41\u0E01\u0E49\u0E44\u0E02\u0E43\u0E0A\u0E49\u0E44\u0E14\u0E49\u0E40\u0E09\u0E1E\u0E32\u0E30 Normal" }, "\u270F\uFE0F \u0E41\u0E01\u0E49\u0E44\u0E02"), editModeMessageForRerun && /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          type: "button",
          onClick: () => {
            if (editModeMessageForRerun && !isTyping) sendMessage(editModeMessageForRerun);
          },
          disabled: isTyping,
          title: "\u0E2A\u0E48\u0E07\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E41\u0E01\u0E49\u0E44\u0E02\u0E17\u0E23\u0E34\u0E1B\u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07 \u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E23\u0E31\u0E19 Flow \u0E43\u0E2B\u0E21\u0E48",
          style: {
            padding: "4px 10px",
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.3)",
            background: "rgba(59, 130, 246, 0.25)",
            color: "#fff",
            cursor: isTyping ? "not-allowed" : "pointer",
            fontSize: "12px",
            opacity: isTyping ? 0.7 : 1
          }
        },
        "\u{1F504} \u0E23\u0E31\u0E19 Flow \u0E43\u0E2B\u0E21\u0E48"
      )), /* @__PURE__ */ import_react13.default.createElement("div", { className: "chat-mode-toggle-desktop" }, /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          onClick: () => {
            if (isEditMode) return;
            setChatMode("normal");
            localStorage.setItem("chat_mode", "normal");
          },
          style: {
            padding: "6px 12px",
            borderRadius: "6px",
            border: "none",
            background: chatMode === "normal" ? "rgba(59, 130, 246, 0.3)" : "transparent",
            color: chatMode === "normal" ? "#fff" : "rgba(255, 255, 255, 0.7)",
            cursor: isEditMode ? "default" : "pointer",
            fontWeight: chatMode === "normal" ? "600" : "400",
            transition: "all 0.2s"
          },
          title: isEditMode ? "\u0E42\u0E2B\u0E21\u0E14\u0E41\u0E01\u0E49\u0E44\u0E02\u0E43\u0E0A\u0E49\u0E44\u0E14\u0E49\u0E40\u0E09\u0E1E\u0E32\u0E30\u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21" : "\u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21 - \u0E04\u0E38\u0E13\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C\u0E40\u0E2D\u0E07"
        },
        "\u{1F4CB} \u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21"
      ), /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          onClick: () => {
            if (isEditMode) return;
            setChatMode("agent");
            localStorage.setItem("chat_mode", "agent");
          },
          disabled: isEditMode,
          style: {
            padding: "6px 12px",
            borderRadius: "6px",
            border: "none",
            background: chatMode === "agent" ? "rgba(139, 92, 246, 0.3)" : "transparent",
            color: isEditMode ? "rgba(255,255,255,0.4)" : chatMode === "agent" ? "#fff" : "rgba(255, 255, 255, 0.7)",
            cursor: isEditMode ? "not-allowed" : "pointer",
            fontWeight: chatMode === "agent" ? "600" : "400",
            transition: "all 0.2s",
            opacity: isEditMode ? 0.6 : 1
          },
          title: isEditMode ? "\u0E42\u0E2B\u0E21\u0E14\u0E41\u0E01\u0E49\u0E44\u0E02\u0E43\u0E0A\u0E49\u0E44\u0E14\u0E49\u0E40\u0E09\u0E1E\u0E32\u0E30\u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21" : "\u0E42\u0E2B\u0E21\u0E14 Agent - AI \u0E14\u0E33\u0E40\u0E19\u0E34\u0E19\u0E01\u0E32\u0E23\u0E40\u0E2D\u0E07\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14"
        },
        "\u{1F916} \u0E42\u0E2B\u0E21\u0E14 Agent"
      )), /* @__PURE__ */ import_react13.default.createElement("div", { className: "chat-mode-toggle-mobile", ref: chatModeDropdownRef }, /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          className: "chat-mode-dropdown-button",
          onClick: () => !isEditMode && setIsChatModeDropdownOpen(!isChatModeDropdownOpen),
          title: isEditMode ? "\u0E42\u0E2B\u0E21\u0E14\u0E41\u0E01\u0E49\u0E44\u0E02\u0E43\u0E0A\u0E49\u0E44\u0E14\u0E49\u0E40\u0E09\u0E1E\u0E32\u0E30\u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21" : chatMode === "normal" ? "\u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21" : "\u0E42\u0E2B\u0E21\u0E14 Agent",
          style: isEditMode ? { cursor: "default" } : {}
        },
        /* @__PURE__ */ import_react13.default.createElement("span", null, chatMode === "normal" ? "\u{1F4CB} \u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21" : "\u{1F916} \u0E42\u0E2B\u0E21\u0E14 Agent"),
        !isEditMode && /* @__PURE__ */ import_react13.default.createElement("svg", { className: "chat-mode-dropdown-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react13.default.createElement("path", { d: "M7 10l5 5 5-5z" }))
      ), isChatModeDropdownOpen && !isEditMode && /* @__PURE__ */ import_react13.default.createElement("div", { className: "chat-mode-dropdown-menu" }, /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          className: `chat-mode-dropdown-item ${chatMode === "normal" ? "active" : ""}`,
          onClick: () => {
            setChatMode("normal");
            localStorage.setItem("chat_mode", "normal");
            setIsChatModeDropdownOpen(false);
          }
        },
        /* @__PURE__ */ import_react13.default.createElement("span", null, "\u{1F4CB} \u0E42\u0E2B\u0E21\u0E14\u0E16\u0E32\u0E21"),
        chatMode === "normal" && /* @__PURE__ */ import_react13.default.createElement("span", { className: "chat-mode-check" }, "\u2713")
      ), /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          className: `chat-mode-dropdown-item ${chatMode === "agent" ? "active" : ""}`,
          onClick: () => {
            setChatMode("agent");
            localStorage.setItem("chat_mode", "agent");
            setIsChatModeDropdownOpen(false);
          }
        },
        /* @__PURE__ */ import_react13.default.createElement("span", null, "\u{1F916} \u0E42\u0E2B\u0E21\u0E14 Agent"),
        chatMode === "agent" && /* @__PURE__ */ import_react13.default.createElement("span", { className: "chat-mode-check" }, "\u2713")
      )))))), connectionError && /* @__PURE__ */ import_react13.default.createElement(
        "div",
        {
          className: "connection-error-banner",
          style: {
            padding: "10px 14px",
            margin: "0 12px 10px",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            borderRadius: "8px",
            color: "#fef2f2",
            fontSize: "13px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "8px"
          }
        },
        /* @__PURE__ */ import_react13.default.createElement("span", { style: { flex: 1, minWidth: 0 } }, "\u26A0\uFE0F ", connectionError),
        /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            type: "button",
            onClick: () => {
              setConnectionError(null);
              checkApiConnection();
            },
            style: {
              padding: "6px 12px",
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.3)",
              background: "rgba(255,255,255,0.15)",
              color: "#fff",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "12px"
            }
          },
          "\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48"
        )
      ), chatMode !== "agent" && /* @__PURE__ */ import_react13.default.createElement(
        BookingProgressBar,
        {
          funnelState: latestBotMessage?.agentState?.booking_funnel_state || "idle"
        }
      ), /* @__PURE__ */ import_react13.default.createElement("div", { className: "messages-area" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "messages-list" }, isLoadingHistory && /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-wrapper message-left" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-content-wrapper" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-bubble", style: { padding: "1rem 1.5rem" } }, /* @__PURE__ */ import_react13.default.createElement("span", { className: "typing-text" }, "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E42\u0E2B\u0E25\u0E14\u0E1B\u0E23\u0E30\u0E27\u0E31\u0E15\u0E34\u0E01\u0E32\u0E23\u0E2A\u0E19\u0E17\u0E19\u0E32"), /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dots" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dot" }), /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dot" }), /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dot" }))))), !isLoadingHistory && activeTrip?._loadError && /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-wrapper message-left" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-content-wrapper" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-bubble message-bot message-error", style: { maxWidth: "85%" } }, /* @__PURE__ */ import_react13.default.createElement("p", { className: "message-text" }, "\u0E42\u0E2B\u0E25\u0E14\u0E1B\u0E23\u0E30\u0E27\u0E31\u0E15\u0E34\u0E41\u0E0A\u0E17\u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08 (\u0E40\u0E0B\u0E34\u0E23\u0E4C\u0E1F\u0E40\u0E27\u0E2D\u0E23\u0E4C\u0E2B\u0E23\u0E37\u0E2D\u0E01\u0E32\u0E23\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E02\u0E31\u0E14\u0E02\u0E49\u0E2D\u0E07) \u0E01\u0E23\u0E38\u0E13\u0E32\u0E25\u0E2D\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E2B\u0E23\u0E37\u0E2D\u0E40\u0E23\u0E34\u0E48\u0E21\u0E41\u0E0A\u0E17\u0E43\u0E2B\u0E21\u0E48")))), !isLoadingHistory && !activeTrip?._loadError && messages.filter((message) => {
        if (message.type === "tool") return false;
        if (isToolCallText(message.text || "")) return false;
        return true;
      }).map((message, msgIdx) => /* @__PURE__ */ import_react13.default.createElement(
        "div",
        {
          key: message.id != null && message.id !== "" ? `msg-${message.id}-${msgIdx}` : `msg-idx-${msgIdx}`,
          className: `message-wrapper ${message.type === "user" ? "message-right" : "message-left"}`
        },
        /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-content-wrapper" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: `message-bubble ${message.type === "user" ? "message-user" : "message-bot"} ${message.type === "bot" && (formatMessageText(message.text)?.includes("\u274C") || formatMessageText(message.text)?.includes("\u0E44\u0E21\u0E48\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08") || formatMessageText(message.text)?.includes("Error:")) ? "message-error" : ""} ${message.type === "bot" && (formatMessageText(message.text)?.includes("\u0E22\u0E31\u0E07\u0E44\u0E21\u0E48\u0E21\u0E35\u0E0B\u0E49\u0E2D\u0E22\u0E2A\u0E4C") || formatMessageText(message.text)?.includes("\u0E44\u0E21\u0E48\u0E21\u0E35\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C") || formatMessageText(message.text)?.includes("\u0E25\u0E2D\u0E07\u0E1E\u0E34\u0E21\u0E1E\u0E4C\u0E17\u0E23\u0E34\u0E1B")) ? "message-empty-state" : ""}` }, /* @__PURE__ */ import_react13.default.createElement("p", { className: "message-text" }, formatMessageText(message.text) || "\xA0"), message.error && message.retryAvailable && message.onRetry && /* @__PURE__ */ import_react13.default.createElement("div", { style: {
          marginTop: "12px",
          padding: "12px",
          background: "rgba(220, 38, 38, 0.1)",
          borderRadius: "8px",
          border: "1px solid rgba(220, 38, 38, 0.3)"
        } }, /* @__PURE__ */ import_react13.default.createElement("p", { style: { marginBottom: "8px", fontSize: "13px", opacity: 0.9 } }, "\u0E44\u0E21\u0E48\u0E2A\u0E32\u0E21\u0E32\u0E23\u0E16\u0E40\u0E0A\u0E37\u0E48\u0E2D\u0E21\u0E15\u0E48\u0E2D\u0E01\u0E31\u0E1A\u0E40\u0E0B\u0E34\u0E23\u0E4C\u0E1F\u0E40\u0E27\u0E2D\u0E23\u0E4C\u0E44\u0E14\u0E49"), /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            onClick: () => {
              if (message.onRetry) {
                message.onRetry();
              }
            },
            style: {
              padding: "6px 16px",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: "500"
            }
          },
          "\u{1F504} \u0E25\u0E2D\u0E07\u0E2D\u0E35\u0E01\u0E04\u0E23\u0E31\u0E49\u0E07"
        )), message.reasoning && /* @__PURE__ */ import_react13.default.createElement("div", { className: "reasoning-light", style: {
          marginTop: "8px",
          padding: "8px 12px",
          background: "rgba(255, 255, 255, 0.1)",
          borderRadius: "8px",
          fontSize: "13px",
          fontStyle: "italic",
          color: "rgba(255, 255, 255, 0.9)"
        } }, "\u{1F4A1} ", message.reasoning), message.memorySuggestions && message.memorySuggestions.length > 0 && /* @__PURE__ */ import_react13.default.createElement("div", { className: "memory-toggle", style: {
          marginTop: "12px",
          padding: "12px",
          background: "rgba(255, 255, 255, 0.15)",
          borderRadius: "8px",
          fontSize: "13px"
        } }, /* @__PURE__ */ import_react13.default.createElement("div", { style: { marginBottom: "8px", fontWeight: "600" } }, "\u{1F4BE} \u0E08\u0E33\u0E44\u0E27\u0E49\u0E43\u0E0A\u0E49\u0E04\u0E23\u0E31\u0E49\u0E07\u0E2B\u0E19\u0E49\u0E32\u0E2B\u0E23\u0E37\u0E2D\u0E44\u0E21\u0E48?"), message.memorySuggestions.map((suggestion, idx) => /* @__PURE__ */ import_react13.default.createElement("div", { key: idx, style: {
          marginBottom: "8px",
          padding: "8px",
          background: "rgba(255, 255, 255, 0.1)",
          borderRadius: "6px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        } }, /* @__PURE__ */ import_react13.default.createElement("span", null, suggestion.description || suggestion.key, ": ", suggestion.value), /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            onClick: () => handleMemoryCommit(suggestion, message.id),
            style: {
              padding: "4px 12px",
              background: "rgba(255, 255, 255, 0.2)",
              border: "1px solid rgba(255, 255, 255, 0.3)",
              borderRadius: "4px",
              color: "#fff",
              cursor: "pointer",
              fontSize: "12px"
            }
          },
          "\u0E08\u0E33\u0E44\u0E27\u0E49"
        )))), message.type === "bot" && message.currentPlan && message.id !== latestBotWithPlan?.id && /* @__PURE__ */ import_react13.default.createElement("div", { className: "current-plan-summary" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "current-plan-title" }, "\u0E41\u0E1E\u0E25\u0E19\u0E17\u0E35\u0E48\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E1B\u0E31\u0E08\u0E08\u0E38\u0E1A\u0E31\u0E19"), /* @__PURE__ */ import_react13.default.createElement("div", { className: "current-plan-body" }, message.currentPlan.trip_meta && /* @__PURE__ */ import_react13.default.createElement("div", { className: "current-plan-row" }, /* @__PURE__ */ import_react13.default.createElement("span", null, message.currentPlan.trip_meta.origin, " \u2192 ", message.currentPlan.trip_meta.destination), message.currentPlan.trip_meta.check_in && message.currentPlan.trip_meta.check_out && /* @__PURE__ */ import_react13.default.createElement("span", null, " ", "\u2022 ", message.currentPlan.trip_meta.check_in, " \u2013 ", message.currentPlan.trip_meta.check_out)), message.currentPlan.summary && /* @__PURE__ */ import_react13.default.createElement("div", { className: "current-plan-price" }, formatPriceInThb(message.currentPlan.summary.total_price, message.currentPlan.summary.currency)))), (() => {
          const plan = selectedPlan || message.currentPlan;
          const hasPlan = !!plan;
          const checkCoreSegmentsReady = (p) => {
            if (!p) {
              console.debug("checkCoreSegmentsReady: No plan provided (this is normal for new chats)");
              return false;
            }
            const flights = p.travel?.flights ? [...p.travel.flights.outbound || [], ...p.travel.flights.inbound || []] : p.flight?.segments?.length > 0 ? p.flight.segments : p.flight?.outbound?.length > 0 || p.flight?.inbound?.length > 0 ? [...p.flight.outbound || [], ...p.flight.inbound || []] : Array.isArray(p.flights) ? p.flights : [];
            const accommodations = p.accommodation?.segments || p.hotel?.segments || p.accommodations || [];
            const ground = p.travel?.ground_transport || p.ground_transport || [];
            if (true) {
              console.debug("checkCoreSegmentsReady:", {
                hasTravelFlights: !!p.travel?.flights,
                flightsCount: flights.length,
                accommodationsCount: accommodations.length,
                flights: flights.map((f) => ({ status: f.status, id: f.selected_option?.id })),
                accommodations: accommodations.map((a) => ({ status: a.status, id: a.selected_option?.id }))
              });
            }
            const isSegmentReady = (seg) => {
              const status = seg?.status || seg?.selected_option?.status;
              if (status) return status === "confirmed" || status === "CONFIRMED" || status === "selected" || status === "SELECTED";
              return !!(seg?.from || seg?.carrier || seg?.hotelName || seg?.hotelId || seg?.selected_option);
            };
            const hasConfirmedFlights = flights.length > 0 && flights.some(isSegmentReady);
            const hasConfirmedHotels = accommodations.length > 0 && accommodations.some(isSegmentReady);
            const hasFlatFlight = !!(p.flight?.segments?.length > 0 || p.flight?.outbound?.length > 0 || p.flight?.carrier || p.flight && (p.flight.departure || p.flight.arrival));
            const hasFlatHotel = !!(p.hotel?.segments?.length > 0 || p.hotel?.hotelName || p.accommodation?.segments?.length > 0);
            const hasSummaryOrPrice = !!(p.total_price != null && p.total_price > 0 || p.summary?.total_price > 0 || p.flight && (p.flight.total_price || p.flight.price));
            if (true) {
              console.debug("Core segments ready:", { hasConfirmedFlights, hasConfirmedHotels, hasFlatFlight, hasFlatHotel, hasSummaryOrPrice });
            }
            return hasConfirmedFlights || hasConfirmedHotels || hasFlatFlight || hasFlatHotel || hasSummaryOrPrice;
          };
          const isCoreReady = checkCoreSegmentsReady(plan);
          const workflowValidation = message.workflowValidation || message.agentState?.workflow_validation || {};
          const currentWorkflowStep = workflowValidation.current_step || message.agentState?.step || "planning";
          const isWorkflowComplete = workflowValidation.is_complete || false;
          const isAgentModeMsg = chatMode === "agent";
          const canShowSummary = currentWorkflowStep === "trip_summary" || currentWorkflowStep === "summary" || currentWorkflowStep === "completed" || currentWorkflowStep === "confirmed" || currentWorkflowStep === "booking" || isCoreReady && isWorkflowComplete || // ✅ Agent mode: แสดงเมื่อ core ready แม้ workflow step ไม่ตรง
          isAgentModeMsg && isCoreReady || // ✅ แสดงเมื่อมี plan + core ready (เที่ยวบิน/ที่พักยืนยันแล้ว) แม้ workflow ยัง selecting (เช่นรอแค่ transfer)
          isCoreReady && hasPlan;
          const isLatestWithPlan = latestBotWithPlan && message.id === latestBotWithPlan.id;
          const messageText = formatMessageText(message.text || "");
          const inputSaysBookNow = /จอง\s*เลย/.test(String(inputText || "").trim());
          const botSaysConfirmOrSummary = /Confirm\s*Booking|ยืนยันการจอง|รายละเอียดครบถ้วน|กด\s*จอง|กด\s*Confirm/i.test(messageText);
          const hasBookNowKeyword = messageText.includes("\u0E08\u0E2D\u0E07\u0E40\u0E25\u0E22") || showTripSummary || editingMessageId && inputSaysBookNow || botSaysConfirmOrSummary;
          const shouldShow = message.type === "bot" && hasPlan && isCoreReady && canShowSummary && !message.text?.includes("\u274C") && isLatestWithPlan && hasBookNowKeyword;
          return shouldShow;
        })() && /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-block full-width-block" }, /* @__PURE__ */ import_react13.default.createElement(
          TripSummaryCard,
          {
            plan: selectedPlan || message.currentPlan,
            travelSlots: selectedTravelSlots || message.travelSlots,
            cachedOptions: message.cachedOptions || finalData?.cached_options,
            cacheValidation: message.cacheValidation || finalData?.cache_validation,
            workflowValidation: message.workflowValidation || message.agentState?.workflow_validation
          }
        ), /* @__PURE__ */ import_react13.default.createElement("div", { className: "slots-container" }, /* @__PURE__ */ import_react13.default.createElement(
          FlightSlotCard,
          {
            flight: selectedPlan?.flight || message.currentPlan?.flight || (selectedTravelSlots?.flight || message.travelSlots?.flight)
          }
        ), /* @__PURE__ */ import_react13.default.createElement(
          TransportSlotCard,
          {
            transport: selectedPlan?.transport || message.currentPlan?.transport || (selectedTravelSlots?.transport || message.travelSlots?.transport)
          }
        ), /* @__PURE__ */ import_react13.default.createElement(
          HotelSlotCard,
          {
            hotel: selectedPlan?.hotel || message.currentPlan?.hotel || (selectedTravelSlots?.hotel || message.travelSlots?.hotel),
            travelSlots: selectedTravelSlots || message.travelSlots
          }
        )), /* @__PURE__ */ import_react13.default.createElement(
          UserInfoCard,
          {
            userProfile,
            onEdit: handleEditUserProfile,
            isDomesticTravel: (() => {
              const slots = selectedTravelSlots || message.travelSlots;
              if (!slots) return false;
              const origin = slots.origin_city || slots.origin || "";
              const dest = slots.destination_city || slots.destination || "";
              return isLocationInThailand(origin) && isLocationInThailand(dest);
            })()
          }
        ), /* @__PURE__ */ import_react13.default.createElement(
          ConfirmBookingCard,
          {
            canBook: (() => {
              if (!selectedPlan || !userProfile) return false;
              const slots = selectedTravelSlots || message.travelSlots || {};
              const origin = slots.origin_city || slots.origin || "";
              const dest = slots.destination_city || slots.destination || "";
              const isInternationalTrip = !(isLocationInThailand(origin) && isLocationInThailand(dest));
              if (!isInternationalTrip) return true;
              const hasPassportInfo = !!(userProfile.passport_no && userProfile.passport_expiry && userProfile.nationality);
              const visaFreeRoute = isVisaFreeRoute(userProfile.nationality, dest);
              const hasVisaInfo = !!(userProfile.visa_type || userProfile.visa_number || Array.isArray(user?.visa_records) && user.visa_records.length > 0);
              return hasPassportInfo && (visaFreeRoute || hasVisaInfo);
            })(),
            onConfirm: handleConfirmBooking,
            onPayment: handlePayment,
            onNavigateToBookings,
            note: "\u0E23\u0E30\u0E1A\u0E1A\u0E08\u0E30\u0E08\u0E2D\u0E07\u0E40\u0E09\u0E1E\u0E32\u0E30 Amadeus Sandbox (test) \u0E40\u0E17\u0E48\u0E32\u0E19\u0E31\u0E49\u0E19",
            isBooking,
            bookingResult: message.bookingResult ?? bookingResult,
            chatMode,
            agentState: latestBotMessage?.agentState || null,
            existingBookingForTrip: existingBookingForTripId === (activeTrip?.tripId || activeTrip?.chatId)
          }
        )), message.type === "bot" && /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, chatMode !== "agent" && message.slotChoices && message.slotChoices.length > 0 && message.slotIntent && (() => {
          const isMulti = message.slotIntent === "multi";
          const filteredCount = isMulti ? message.slotChoices.length : message.slotChoices.filter((choice) => {
            if (message.slotIntent === "transport" || message.slotIntent === "transfer") {
              return choice.category === "transport" || choice.category === "transfer";
            }
            return choice.category === message.slotIntent;
          }).length;
          if (filteredCount === 0) return null;
          return /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-summary-in-bubble" }, /* @__PURE__ */ import_react13.default.createElement("span", { className: "summary-icon" }, "\u{1F4DD}"), /* @__PURE__ */ import_react13.default.createElement("span", { className: "summary-text" }, message.slotIntent === "flight" && "\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19", message.slotIntent === "hotel" && "\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01", (message.slotIntent === "transport" || message.slotIntent === "transfer") && "\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07", (message.slotIntent === "multi" || !["flight", "hotel", "transport", "transfer"].includes(message.slotIntent)) && "\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01", " ", "(", filteredCount, " \u0E23\u0E32\u0E22\u0E01\u0E32\u0E23)"));
        })(), (() => {
          if (chatMode === "agent") return null;
          const hasPlanChoices = message.planChoices && Array.isArray(message.planChoices) && message.planChoices.length > 0;
          const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
          const shouldShowPlanChoices = hasPlanChoices && (!hasSlotChoices || !message.slotIntent);
          return shouldShowPlanChoices ? /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-summary-in-bubble" }, /* @__PURE__ */ import_react13.default.createElement("span", { className: "summary-icon" }, "\u2708\uFE0F"), /* @__PURE__ */ import_react13.default.createElement("span", { className: "summary-text" }, "\u0E41\u0E1C\u0E19\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E17\u0E35\u0E48\u0E08\u0E31\u0E14\u0E43\u0E2B\u0E49\u0E17\u0E31\u0E49\u0E07\u0E2B\u0E21\u0E14 ", message.planChoices.length, " \u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C")) : null;
        })())), message.type === "bot" && /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, isAdmin && (() => {
          console.log("\u{1F6E0}\uFE0F Admin Debug - Message slotChoices:", {
            hasSlotChoices: !!message.slotChoices,
            slotChoicesLength: message.slotChoices?.length || 0,
            slotIntent: message.slotIntent,
            slotChoices: message.slotChoices
          });
          return null;
        })(), message.slotChoices && message.slotChoices.length > 0 && (() => {
          if (chatMode === "agent") return null;
          const isLatestWithChoices = latestBotWithChoices && message.id === latestBotWithChoices.id;
          const effectiveIntent = message.slotIntent || null;
          const flightSelected = message.id != null && messageIdsWithFlightSelected.has(message.id);
          const hotelSelected = message.id != null && messageIdsWithHotelSelected.has(message.id);
          const getCat = (c) => {
            if (c.category === "flight") return "flight";
            if (c.category === "hotel") return "hotel";
            if (c.category === "transport" || c.category === "transfer") return "transport";
            if (c.flight && (c.flight.segments?.length > 0 || c.flight.outbound?.length || c.flight.inbound?.length)) return "flight";
            if (c.hotel) return "hotel";
            if (c.transport || c.car || c.ground_transport) return "transport";
            return null;
          };
          const flightChoices = message.slotChoices.filter((c) => getCat(c) === "flight");
          const hotelChoices = message.slotChoices.filter((c) => getCat(c) === "hotel");
          const transportChoices = message.slotChoices.filter((c) => getCat(c) === "transport");
          const hasMulti = effectiveIntent === "multi" || flightChoices.length > 0 && hotelChoices.length > 0 || flightChoices.length > 0 && transportChoices.length > 0 || hotelChoices.length > 0 && transportChoices.length > 0;
          const showHotel = hotelChoices.length > 0 && (flightChoices.length === 0 || flightSelected);
          const showTransport = transportChoices.length > 0 && (hotelChoices.length === 0 || hotelSelected);
          const filteredChoices = hasMulti ? [
            ...flightChoices,
            ...showHotel ? hotelChoices : [],
            ...showTransport ? transportChoices : []
          ] : message.slotChoices.filter((choice) => {
            if (!effectiveIntent || effectiveIntent === "multi") return true;
            if (effectiveIntent === "transport" || effectiveIntent === "transfer") return choice.category === "transport" || choice.category === "transfer";
            return choice.category === effectiveIntent;
          });
          if (!isLatestWithChoices) {
            return /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-summary-compact", key: "slot-summary-old" }, /* @__PURE__ */ import_react13.default.createElement("span", { className: "summary-text" }, "\u2708\uFE0F \u0E21\u0E35 ", message.slotChoices.length, " \u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E43\u0E2B\u0E49\u0E40\u0E25\u0E37\u0E2D\u0E01 (\u0E14\u0E39\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E25\u0E48\u0E32\u0E2A\u0E38\u0E14\u0E14\u0E49\u0E32\u0E19\u0E25\u0E48\u0E32\u0E07)"));
          }
          const getSlotCardComponent = (intent, choice) => {
            if (!choice || typeof choice !== "object") return PlanChoiceCard;
            const cat = intent || getCat(choice);
            if (cat === "flight") return choice.flight && (choice.flight.segments?.length > 0 || choice.flight.outbound?.length || choice.flight.inbound?.length) ? PlanChoiceCardFlights : PlanChoiceCard;
            if (cat === "hotel") return choice.hotel ? PlanChoiceCardHotels : PlanChoiceCard;
            if (cat === "transport" || cat === "transfer") return choice.transport || choice.car || choice.ground_transport ? PlanChoiceCardTransfer : PlanChoiceCard;
            return PlanChoiceCard;
          };
          if (filteredChoices.length === 0) return null;
          const outboundAlreadySelected = message.id != null && messageIdsWithOutboundSelected.has(message.id);
          const isInboundFlightChoice = (c) => c?.flight_direction === "inbound" || c?.flight?.segments?.[0]?.direction && String(c.flight.segments[0].direction).includes("\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A");
          const sortedChoices = effectiveIntent === "flight" && flightChoices.length > 0 ? [...filteredChoices].sort((a, b) => (isInboundFlightChoice(a) ? 1 : 0) - (isInboundFlightChoice(b) ? 1 : 0)) : filteredChoices;
          return /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-block full-width-block", key: "slot-choices-block" }, isAdmin && console.log("\u{1F6E0}\uFE0F Admin Debug - Rendering PlanChoiceCard grid:", sortedChoices.length, "slotIntent:", effectiveIntent), /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-grid" }, sortedChoices.map((choice, idx) => {
            const intent = effectiveIntent || getCat(choice);
            const SlotCard = getSlotCardComponent(intent, choice);
            const stableKey = `slot-${String(message.id ?? "")}-${idx}-${choice.id ?? choice._original_id ?? idx}`;
            const isFlightInbound = intent === "flight" && isInboundFlightChoice(choice);
            const disableSelect = isFlightInbound && !outboundAlreadySelected;
            const cardStyle = getChoiceCardStyle(choice, idx, sortedChoices.length, `slot-${message.id || "msg"}`);
            return /* @__PURE__ */ import_react13.default.createElement(
              SlotCard,
              {
                key: stableKey,
                choice,
                onSelect: disableSelect ? void 0 : (id) => handleSelectSlotChoice(id, intent || getCat(choice), choice, message),
                disableSelect,
                cardStyle
              }
            );
          })));
        })(), isAdmin && message.slotChoices && message.slotChoices.length > 0 && !message.slotIntent && console.log("\u26A0\uFE0F Admin Debug - slotChoices shown with inferred category (no slotIntent):", message.slotChoices.length), isAdmin && message.slotIntent && (!message.slotChoices || message.slotChoices.length === 0) && console.log("\u26A0\uFE0F Admin Debug - slotIntent exists but no slotChoices:", message.slotIntent), (() => {
          if (chatMode === "agent") return null;
          const hasPlanChoices = message.planChoices && Array.isArray(message.planChoices) && message.planChoices.length > 0;
          const hasSlotChoices = message.slotChoices && message.slotChoices.length > 0;
          const shouldShowPlanChoices = hasPlanChoices && (!hasSlotChoices || !message.slotIntent);
          const isLatestWithChoices = latestBotWithChoices && message.id === latestBotWithChoices.id;
          if (!shouldShowPlanChoices) return null;
          if (!isLatestWithChoices) {
            return /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-summary-compact", key: "plan-summary-old" }, /* @__PURE__ */ import_react13.default.createElement("span", { className: "summary-text" }, "\u2708\uFE0F \u0E41\u0E1C\u0E19\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E17\u0E35\u0E48\u0E08\u0E31\u0E14\u0E43\u0E2B\u0E49 ", message.planChoices.length, " \u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C (\u0E14\u0E39\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E25\u0E48\u0E32\u0E2A\u0E38\u0E14\u0E14\u0E49\u0E32\u0E19\u0E25\u0E48\u0E32\u0E07)"));
          }
          const getPlanCardComponent = (choice) => {
            if (!choice || typeof choice !== "object") return PlanChoiceCard;
            const cat = choice.category || (choice.flight ? "flight" : choice.hotel ? "hotel" : choice.transport || choice.car ? "transport" : null);
            if (cat === "flight") return choice.flight && (choice.flight.segments?.length > 0 || choice.flight.outbound?.length || choice.flight.inbound?.length) ? PlanChoiceCardFlights : PlanChoiceCard;
            if (cat === "hotel") return choice.hotel ? PlanChoiceCardHotels : PlanChoiceCard;
            if (cat === "transport" || cat === "transfer") return choice.transport || choice.car || choice.ground_transport ? PlanChoiceCardTransfer : PlanChoiceCard;
            return PlanChoiceCard;
          };
          return /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-block full-width-block" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "plan-choices-grid" }, message.planChoices.map((choice, idx) => {
            const PlanCard = getPlanCardComponent(choice);
            const cardStyle = getChoiceCardStyle(choice, idx, message.planChoices.length, `plan-${message.id || "msg"}`);
            return /* @__PURE__ */ import_react13.default.createElement(
              PlanCard,
              {
                key: choice.id || `choice-${choice.title || ""}-${idx}`,
                choice,
                onSelect: (id) => handleSelectPlanChoice(id, choice),
                cardStyle
              }
            );
          })));
        })()), message.type === "user" && message.id === lastUserMessageId && /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-actions message-actions-user" }, /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            className: "btn-action btn-refresh",
            onClick: () => regenerateFromUserText(message.id, message.text),
            disabled: isTyping,
            title: "\u0E23\u0E35\u0E40\u0E1F\u0E23\u0E0A"
          },
          "\u{1F504} \u0E23\u0E35\u0E40\u0E1F\u0E23\u0E0A"
        ), /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            className: "btn-action btn-edit",
            onClick: () => handleEditMessage(message.id, message.text),
            disabled: isTyping,
            title: "\u0E41\u0E01\u0E49\u0E44\u0E02"
          },
          "\u270F\uFE0F \u0E41\u0E01\u0E49\u0E44\u0E02"
        ), isTyping && /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            className: "btn-action btn-stop",
            onClick: handleStop,
            title: "\u0E2B\u0E22\u0E38\u0E14"
          },
          "\u23F9\uFE0F \u0E2B\u0E22\u0E38\u0E14"
        )), message.type === "bot" && /* @__PURE__ */ import_react13.default.createElement("div", { className: "message-actions message-actions-bot" }, /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            className: "btn-action btn-refresh",
            onClick: () => {
              const tripMessages = activeTrip?.messages || [];
              const botIdx = tripMessages.findIndex((m) => m.id === message.id);
              const before = tripMessages.slice(0, botIdx);
              const userMsg = [...before].reverse().find((m) => m.type === "user");
              if (userMsg) {
                handleRefreshBot(userMsg.id, userMsg.text);
              }
            },
            disabled: isTyping || (() => {
              const tripMessages = activeTrip?.messages || [];
              const botIdx = tripMessages.findIndex((m) => m.id === message.id);
              const before = tripMessages.slice(0, botIdx);
              const userMsg = [...before].reverse().find((m) => m.type === "user");
              return !userMsg;
            })(),
            title: "\u0E23\u0E35\u0E40\u0E1F\u0E23\u0E0A"
          },
          "\u{1F504} \u0E23\u0E35\u0E40\u0E1F\u0E23\u0E0A"
        ), isTyping && /* @__PURE__ */ import_react13.default.createElement(
          "button",
          {
            className: "btn-action btn-stop",
            onClick: handleStop,
            title: "\u0E2B\u0E22\u0E38\u0E14"
          },
          "\u23F9\uFE0F \u0E2B\u0E22\u0E38\u0E14"
        )))
      )), isTyping && /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-indicator" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-bubble" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "agent-activity-container" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "agent-activity-icon" }, /* @__PURE__ */ import_react13.default.createElement("svg", { width: "16", height: "16", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2" }, /* @__PURE__ */ import_react13.default.createElement("circle", { cx: "12", cy: "12", r: "10", opacity: "0.3" }), /* @__PURE__ */ import_react13.default.createElement("circle", { cx: "12", cy: "12", r: "2", className: "agent-cursor-pulse" }))), /* @__PURE__ */ import_react13.default.createElement("div", { className: "agent-activity-content" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-text" }, getTypingText()), agentStatus?.step && agentStatus.step !== "heartbeat" && getToolInfo(agentStatus.step) && /* @__PURE__ */ import_react13.default.createElement("div", { className: "tool-info", style: {
        fontSize: "12px",
        color: "rgba(255, 255, 255, 0.7)",
        marginTop: "8px",
        marginBottom: "8px",
        fontStyle: "italic"
      } }, getToolInfo(agentStatus.step)), agentStatus && (() => {
        const stepMap = {
          // Thinking & Planning
          "thinking": "\u{1F914} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E34\u0E14...",
          "recall_start": "\u{1F9E0} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E23\u0E30\u0E25\u0E36\u0E01\u0E04\u0E27\u0E32\u0E21\u0E08\u0E33...",
          "controller_start": "\u{1F504} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E23\u0E34\u0E48\u0E21\u0E15\u0E49\u0E19\u0E1B\u0E23\u0E30\u0E21\u0E27\u0E25\u0E1C\u0E25...",
          "controller_iter_1": "\u{1F504} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E1B\u0E23\u0E30\u0E21\u0E27\u0E25\u0E1C\u0E25 (\u0E23\u0E2D\u0E1A\u0E17\u0E35\u0E48 1/2)...",
          "controller_iter_2": "\u{1F504} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E1B\u0E23\u0E30\u0E21\u0E27\u0E25\u0E1C\u0E25 (\u0E23\u0E2D\u0E1A\u0E17\u0E35\u0E48 2/2)...",
          "controller_iter_3": "\u{1F504} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E1B\u0E23\u0E30\u0E21\u0E27\u0E25\u0E1C\u0E25 (\u0E23\u0E2D\u0E1A\u0E17\u0E35\u0E48 2/2)...",
          // Actions
          "create_itinerary": "\u{1F4CB} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E23\u0E49\u0E32\u0E07\u0E41\u0E1C\u0E19\u0E01\u0E32\u0E23\u0E40\u0E14\u0E34\u0E19\u0E17\u0E32\u0E07...",
          "update_req": "\u{1F4DD} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E2D\u0E31\u0E1B\u0E40\u0E14\u0E15\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25\u0E17\u0E23\u0E34\u0E1B...",
          "call_search": "\u{1F50D} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32...",
          "select_option": "\u2705 \u0E01\u0E33\u0E25\u0E31\u0E07\u0E1A\u0E31\u0E19\u0E17\u0E36\u0E01\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01...",
          // Broker-style searching messages
          "searching": "\u{1F50D} \u0E19\u0E32\u0E22\u0E2B\u0E19\u0E49\u0E32\u0E01\u0E33\u0E25\u0E31\u0E07\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E43\u0E2B\u0E49\u0E04\u0E38\u0E13...",
          "searching_flights": "\u2708\uFE0F \u0E19\u0E32\u0E22\u0E2B\u0E19\u0E49\u0E32\u0E01\u0E33\u0E25\u0E31\u0E07\u0E15\u0E23\u0E27\u0E08\u0E2A\u0E2D\u0E1A\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E17\u0E35\u0E48\u0E40\u0E2B\u0E21\u0E32\u0E30\u0E2A\u0E21...",
          "searching_hotels": "\u{1F3E8} \u0E19\u0E32\u0E22\u0E2B\u0E19\u0E49\u0E32\u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E31\u0E14\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01\u0E17\u0E35\u0E48\u0E40\u0E2B\u0E21\u0E32\u0E30\u0E01\u0E31\u0E1A\u0E04\u0E38\u0E13...",
          "call_search_done": "\u2705 \u0E04\u0E49\u0E19\u0E2B\u0E32\u0E40\u0E2A\u0E23\u0E47\u0E08\u0E41\u0E25\u0E49\u0E27 \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E31\u0E14\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E14\u0E35\u0E17\u0E35\u0E48\u0E2A\u0E38\u0E14...",
          // Agent Mode - Auto Selection & Booking
          "agent_auto_select": "\u{1F916} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C\u0E17\u0E35\u0E48\u0E14\u0E35\u0E17\u0E35\u0E48\u0E2A\u0E38\u0E14...",
          "agent_auto_select_immediate": "\u{1F916} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C\u0E17\u0E31\u0E19\u0E17\u0E35...",
          "agent_auto_select_final": "\u{1F916} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E0A\u0E49\u0E2D\u0E22\u0E2A\u0E4C (\u0E23\u0E2D\u0E1A\u0E2A\u0E38\u0E14\u0E17\u0E49\u0E32\u0E22)...",
          "agent_analyze_flights_outbound": "\u{1F4CA} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E34\u0E40\u0E04\u0E23\u0E32\u0E30\u0E2B\u0E4C\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E02\u0E32\u0E44\u0E1B...",
          "agent_analyze_flights_inbound": "\u{1F4CA} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E34\u0E40\u0E04\u0E23\u0E32\u0E30\u0E2B\u0E4C\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A...",
          "agent_analyze_accommodation": "\u{1F4CA} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E34\u0E40\u0E04\u0E23\u0E32\u0E30\u0E2B\u0E4C\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01...",
          "agent_select_flights_outbound": "\u2705 \u0E40\u0E25\u0E37\u0E2D\u0E01\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E02\u0E32\u0E44\u0E1B\u0E41\u0E25\u0E49\u0E27",
          "agent_select_flights_inbound": "\u2705 \u0E40\u0E25\u0E37\u0E2D\u0E01\u0E40\u0E17\u0E35\u0E48\u0E22\u0E27\u0E1A\u0E34\u0E19\u0E02\u0E32\u0E01\u0E25\u0E31\u0E1A\u0E41\u0E25\u0E49\u0E27",
          "agent_select_accommodation": "\u2705 \u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E1E\u0E31\u0E01\u0E41\u0E25\u0E49\u0E27",
          "agent_auto_book": "\u{1F4B3} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E08\u0E2D\u0E07\u0E17\u0E23\u0E34\u0E1B\u0E17\u0E31\u0E19\u0E17\u0E35...",
          // Analyzing
          "analyzing": "\u{1F4CA} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E34\u0E40\u0E04\u0E23\u0E32\u0E30\u0E2B\u0E4C\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25...",
          "planning": "\u{1F4CB} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E32\u0E07\u0E41\u0E1C\u0E19\u0E17\u0E23\u0E34\u0E1B...",
          "selecting": "\u{1F3AF} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E15\u0E31\u0E27\u0E40\u0E25\u0E37\u0E2D\u0E01\u0E17\u0E35\u0E48\u0E14\u0E35\u0E17\u0E35\u0E48\u0E2A\u0E38\u0E14...",
          "confirming": "\u2705 \u0E01\u0E33\u0E25\u0E31\u0E07\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E02\u0E49\u0E2D\u0E21\u0E39\u0E25...",
          "booking": "\u{1F4B3} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E08\u0E2D\u0E07\u0E17\u0E23\u0E34\u0E1B...",
          // Broker-specific steps
          "confirming_search": "\u{1F4CB} \u0E19\u0E32\u0E22\u0E2B\u0E19\u0E49\u0E32\u0E01\u0E33\u0E25\u0E31\u0E07\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E17\u0E23\u0E34\u0E1B\u0E01\u0E48\u0E2D\u0E19\u0E04\u0E49\u0E19\u0E2B\u0E32...",
          "agent_auto_book_success": "\u{1F389} \u0E08\u0E2D\u0E07\u0E2A\u0E33\u0E40\u0E23\u0E47\u0E08\u0E41\u0E25\u0E49\u0E27! \u0E14\u0E39\u0E23\u0E32\u0E22\u0E25\u0E30\u0E40\u0E2D\u0E35\u0E22\u0E14\u0E43\u0E19 My Bookings",
          // Responding
          "acting": "\u2699\uFE0F \u0E01\u0E33\u0E25\u0E31\u0E07\u0E14\u0E33\u0E40\u0E19\u0E34\u0E19\u0E01\u0E32\u0E23...",
          "speaking": "\u{1F4AC} \u0E19\u0E32\u0E22\u0E2B\u0E19\u0E49\u0E32\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E23\u0E38\u0E1B\u0E04\u0E33\u0E41\u0E19\u0E30\u0E19\u0E33...",
          "responder_start": "\u{1F4AC} \u0E19\u0E32\u0E22\u0E2B\u0E19\u0E49\u0E32\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E23\u0E38\u0E1B\u0E04\u0E33\u0E41\u0E19\u0E30\u0E19\u0E33..."
        };
        const statusMap = {
          "thinking": "\u{1F914} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E34\u0E14...",
          "recall": "\u{1F9E0} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E23\u0E30\u0E25\u0E36\u0E01\u0E04\u0E27\u0E32\u0E21\u0E08\u0E33...",
          "searching": "\u{1F50D} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E04\u0E49\u0E19\u0E2B\u0E32...",
          "processing": "\u2699\uFE0F \u0E01\u0E33\u0E25\u0E31\u0E07\u0E1B\u0E23\u0E30\u0E21\u0E27\u0E25\u0E1C\u0E25...",
          "analyzing": "\u{1F4CA} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E34\u0E40\u0E04\u0E23\u0E32\u0E30\u0E2B\u0E4C...",
          "planning": "\u{1F4CB} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E27\u0E32\u0E07\u0E41\u0E1C\u0E19...",
          "acting": "\u2699\uFE0F \u0E01\u0E33\u0E25\u0E31\u0E07\u0E14\u0E33\u0E40\u0E19\u0E34\u0E19\u0E01\u0E32\u0E23...",
          "selecting": "\u{1F3AF} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E40\u0E25\u0E37\u0E2D\u0E01...",
          "confirming": "\u2705 \u0E01\u0E33\u0E25\u0E31\u0E07\u0E22\u0E37\u0E19\u0E22\u0E31\u0E19...",
          "booking": "\u{1F4B3} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E08\u0E2D\u0E07...",
          "speaking": "\u{1F4AC} \u0E01\u0E33\u0E25\u0E31\u0E07\u0E15\u0E2D\u0E1A..."
        };
        return /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, agentStatus.step && agentStatus.step !== "heartbeat" && /* @__PURE__ */ import_react13.default.createElement("div", { className: "agent-activity-step" }, stepMap[agentStatus.step] || `\u2699\uFE0F ${agentStatus.step}`), agentStatus.message && agentStatus.message !== getTypingText() && (() => {
          const message = agentStatus.message || "";
          const stepText = agentStatus.step ? stepMap[agentStatus.step] || agentStatus.step : "";
          if (message && message !== stepText && message !== getTypingText()) {
            let detailMessage = message;
            if (stepText && detailMessage.includes(stepText)) {
              detailMessage = detailMessage.replace(stepText, "").trim();
            }
            const stepEmoji = stepText.match(/^([🤔🧠🔄📋📝🔍✈️🏨📊🎯✅💳⚙️💬])\s*/)?.[1];
            if (stepEmoji && detailMessage.startsWith(stepEmoji)) {
              detailMessage = detailMessage.replace(/^[🤔🧠🔄📋📝🔍✈️🏨📊🎯✅💳⚙️💬]\s*/, "").trim();
            }
            if (detailMessage && detailMessage.length > 0 && detailMessage !== stepText) {
              return /* @__PURE__ */ import_react13.default.createElement("div", { className: "agent-activity-detail" }, detailMessage);
            }
          }
          return null;
        })(), agentStatus.status && agentStatus.status !== "heartbeat" && agentStatus.status !== "thinking" && agentStatus.status !== agentStatus.step && !agentStatus.message?.includes(statusMap[agentStatus.status] || agentStatus.status) && /* @__PURE__ */ import_react13.default.createElement("div", { className: "agent-activity-status" }, statusMap[agentStatus.status] || `\u{1F4CC} ${agentStatus.status}`));
      })())), /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dots" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dot" }), /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dot" }), /* @__PURE__ */ import_react13.default.createElement("div", { className: "typing-dot" })))), /* @__PURE__ */ import_react13.default.createElement("div", { ref: messagesEndRef }))), /* @__PURE__ */ import_react13.default.createElement("div", { className: "input-area" }, editingMessageId && /* @__PURE__ */ import_react13.default.createElement("div", { className: "edit-mode-banner" }, /* @__PURE__ */ import_react13.default.createElement("span", { className: "edit-mode-banner-icon" }, "\u270F\uFE0F"), /* @__PURE__ */ import_react13.default.createElement("span", { className: "edit-mode-banner-text" }, "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E41\u0E01\u0E49\u0E44\u0E02\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21 \u2014 \u0E41\u0E01\u0E49\u0E44\u0E02\u0E41\u0E25\u0E49\u0E27\u0E01\u0E14 Send \u0E2B\u0E23\u0E37\u0E2D Enter"), /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          className: "edit-mode-cancel-btn",
          onClick: () => {
            setEditingMessageId(null);
            setInputText("");
          },
          title: "\u0E22\u0E01\u0E40\u0E25\u0E34\u0E01\u0E01\u0E32\u0E23\u0E41\u0E01\u0E49\u0E44\u0E02"
        },
        "\u2715 \u0E22\u0E01\u0E40\u0E25\u0E34\u0E01"
      )), /* @__PURE__ */ import_react13.default.createElement("div", { className: `input-wrapper${editingMessageId ? " input-wrapper-editing" : ""}` }, /* @__PURE__ */ import_react13.default.createElement(
        "textarea",
        {
          ref: inputRef,
          value: inputText,
          onChange: (e) => setInputText(e.target.value),
          onKeyPress: handleKeyPress,
          placeholder: editingMessageId ? "\u0E41\u0E01\u0E49\u0E44\u0E02\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E41\u0E25\u0E49\u0E27\u0E01\u0E14 Enter \u0E2B\u0E23\u0E37\u0E2D Send..." : t("chat.inputPlaceholder"),
          rows: "1",
          className: `input-field${editingMessageId ? " input-field-editing" : ""}`
        }
      ), /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          onClick: handleVoiceInput,
          className: `btn-mic ${isVoiceMode ? "btn-mic-active" : ""}`,
          title: isVoiceMode ? "\u0E01\u0E14\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E2B\u0E22\u0E38\u0E14\u0E01\u0E32\u0E23\u0E2A\u0E19\u0E17\u0E19\u0E32\u0E14\u0E49\u0E27\u0E22\u0E40\u0E2A\u0E35\u0E22\u0E07" : "\u0E01\u0E14\u0E40\u0E1E\u0E37\u0E48\u0E2D\u0E40\u0E23\u0E34\u0E48\u0E21\u0E2A\u0E19\u0E17\u0E19\u0E32\u0E01\u0E31\u0E1A Agent \u0E14\u0E49\u0E27\u0E22\u0E40\u0E2A\u0E35\u0E22\u0E07"
        },
        isVoiceMode ? (
          /* กำลังใช้งาน → แสดง stop square สีแดง */
          /* @__PURE__ */ import_react13.default.createElement("svg", { className: "mic-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react13.default.createElement("rect", { x: "5", y: "5", width: "14", height: "14", rx: "2" }))
        ) : (
          /* ปกติ → แสดงไมค์ */
          /* @__PURE__ */ import_react13.default.createElement("svg", { className: "mic-icon", fill: "currentColor", viewBox: "0 0 24 24" }, /* @__PURE__ */ import_react13.default.createElement("path", { d: "M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" }), /* @__PURE__ */ import_react13.default.createElement("path", { d: "M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" }))
        )
      ), isTyping ? /* @__PURE__ */ import_react13.default.createElement("button", { onClick: handleStop, className: "btn-send btn-send-stop", title: "\u0E2B\u0E22\u0E38\u0E14\u0E01\u0E32\u0E23\u0E17\u0E33\u0E07\u0E32\u0E19" }, /* @__PURE__ */ import_react13.default.createElement("svg", { fill: "currentColor", viewBox: "0 0 24 24", width: "18", height: "18" }, /* @__PURE__ */ import_react13.default.createElement("rect", { x: "4", y: "4", width: "16", height: "16", rx: "2" }))) : /* @__PURE__ */ import_react13.default.createElement("button", { onClick: handleSend, disabled: !inputText.trim(), className: "btn-send" }, "Send")), isVoiceMode && /* @__PURE__ */ import_react13.default.createElement("div", { className: "voice-conversation-status" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "voice-status-indicator" }, isRecording ? /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, /* @__PURE__ */ import_react13.default.createElement("span", { className: "voice-pulse" }, "\u{1F3A4}"), /* @__PURE__ */ import_react13.default.createElement("span", null, "\u0E01\u0E33\u0E25\u0E31\u0E07\u0E1F\u0E31\u0E07... \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22")) : /* @__PURE__ */ import_react13.default.createElement(import_react13.default.Fragment, null, /* @__PURE__ */ import_react13.default.createElement("span", null, "\u{1F4AC}"), /* @__PURE__ */ import_react13.default.createElement("span", null, "\u0E23\u0E2D Agent \u0E15\u0E2D\u0E1A\u0E01\u0E25\u0E31\u0E1A\u0E14\u0E49\u0E27\u0E22\u0E40\u0E2A\u0E35\u0E22\u0E07..."))), voiceDraft && /* @__PURE__ */ import_react13.default.createElement("div", { className: "voice-draft-preview" }, /* @__PURE__ */ import_react13.default.createElement("div", { className: "voice-draft-label" }, "\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E17\u0E35\u0E48\u0E44\u0E14\u0E49\u0E22\u0E34\u0E19:"), /* @__PURE__ */ import_react13.default.createElement("div", { className: "voice-draft-text" }, voiceDraft), /* @__PURE__ */ import_react13.default.createElement("div", { className: "voice-draft-actions" }, /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          type: "button",
          className: "btn-voice-confirm",
          onClick: () => {
            const text = voiceDraft.trim();
            if (!text) return;
            voiceAwaitingResponseRef.current = true;
            setIsRecording(false);
            setVoiceModeNotice("\u0E01\u0E33\u0E25\u0E31\u0E07\u0E2A\u0E48\u0E07\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E43\u0E2B\u0E49 AI...");
            sendMessage(text);
            setVoiceDraft("");
          }
        },
        "\u0E2A\u0E48\u0E07\u0E02\u0E49\u0E2D\u0E04\u0E27\u0E32\u0E21\u0E19\u0E35\u0E49"
      ), /* @__PURE__ */ import_react13.default.createElement(
        "button",
        {
          type: "button",
          className: "btn-voice-clear",
          onClick: () => {
            setVoiceDraft("");
            if (isVoiceModeRef.current && recognitionRef.current) {
              try {
                recognitionRef.current.start();
                setIsRecording(true);
                setVoiceModeNotice("\u0E42\u0E2B\u0E21\u0E14\u0E40\u0E2A\u0E35\u0E22\u0E07\u0E43\u0E2B\u0E21\u0E48\u0E1E\u0E23\u0E49\u0E2D\u0E21\u0E43\u0E0A\u0E49\u0E07\u0E32\u0E19: \u0E1E\u0E39\u0E14\u0E44\u0E14\u0E49\u0E40\u0E25\u0E22");
              } catch (_) {
              }
            }
          }
        },
        "\u0E1E\u0E39\u0E14\u0E43\u0E2B\u0E21\u0E48"
      ))), voiceModeNotice && /* @__PURE__ */ import_react13.default.createElement("div", { className: "text-xs text-amber-700 mt-1" }, voiceModeNotice)), /* @__PURE__ */ import_react13.default.createElement("div", { className: "powered-by" }, t("chat.poweredBy"))))
    )));
  }
})();
/*! Bundled license information:

react/cjs/react.development.js:
  (**
   * @license React
   * react.development.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

sweetalert2/dist/sweetalert2.all.js:
  (*!
  * sweetalert2 v11.26.17
  * Released under the MIT License.
  *)
*/
