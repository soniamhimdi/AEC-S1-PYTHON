from pithon.evaluator.envframe import EnvFrame
from pithon.evaluator.primitive import check_type, get_primitive_dict
from pithon.syntax import (
    PiAssignment, PiBinaryOperation, PiNumber, PiBool, PiStatement, PiProgram, PiSubscript, PiVariable,
    PiIfThenElse, PiNot, PiAnd, PiOr, PiWhile, PiNone, PiList, PiTuple, PiString,
    PiFunctionDef, PiFunctionCall, PiFor, PiBreak, PiContinue, PiIn, PiReturn, PiClassDef, PiAttribute, PiAttributeAssignment
)
from pithon.evaluator.envvalue import EnvValue, VFunctionClosure, VList, VNone, VTuple, VNumber, VBool, VString, VClassDef,VObject,VMethodClosure


def initial_env() -> EnvFrame:
    """Crée et retourne l'environnement initial avec les primitives."""
    env = EnvFrame()
    env.vars.update(get_primitive_dict())
    return env

def lookup(env: EnvFrame, name: str) -> EnvValue:
    """Recherche une variable dans l'environnement."""
    return env.lookup(name)

def insert(env: EnvFrame, name: str, value: EnvValue) -> None:
    """Insère une variable dans l'environnement."""
    env.insert(name, value)

def evaluate(node: PiProgram, env: EnvFrame) -> EnvValue:
    """Évalue un programme ou une liste d'instructions."""
    if isinstance(node, list):
        last_value = VNone(value=None)
        for stmt in node:
            last_value = evaluate_stmt(stmt, env)
        return last_value
    elif isinstance(node, PiStatement):
        return evaluate_stmt(node, env)
    else:
        raise TypeError(f"Type de nœud non supporté : {type(node)}")

def evaluate_stmt(node: PiStatement, env: EnvFrame) -> EnvValue: 
    """Évalue une instruction ou expression Pithon."""

    if isinstance(node, PiNumber):
        return VNumber(node.value)
   
    elif isinstance(node, PiClassDef):
        return _evaluate_class_def(node, env)
        
    elif isinstance(node, PiAttribute):
        return _evaluate_attribute(node, env)
        
    elif isinstance(node, PiAttributeAssignment):
         return _evaluate_attribute_assignment(node, env)
 
    elif isinstance(node, PiBool):
        return VBool(node.value)

    elif isinstance(node, PiNone):
        return VNone(node.value)

    elif isinstance(node, PiString):
        return VString(node.value)

    elif isinstance(node, PiList):
        elements = [evaluate_stmt(e, env) for e in node.elements]
        return VList(elements)

    elif isinstance(node, PiTuple):
        elements = tuple(evaluate_stmt(e, env) for e in node.elements)
        return VTuple(elements)

    elif isinstance(node, PiVariable):
        return lookup(env, node.name)

    elif isinstance(node, PiBinaryOperation):
        # Traite l'opération binaire comme un appel de fonction
        fct_call = PiFunctionCall(
            function=PiVariable(name=node.operator),
            args=[node.left, node.right]
        )
        return evaluate_stmt(fct_call, env)

    elif isinstance(node, PiAssignment):
        value = evaluate_stmt(node.value, env)
        insert(env, node.name, value)
        return value
    
    elif isinstance(node, PiIfThenElse):
        cond = evaluate_stmt(node.condition, env)
        cond = check_type(cond, VBool)
        branch = node.then_branch if cond.value else node.else_branch
        last_value = evaluate(branch, env)
        return last_value

    elif isinstance(node, PiNot):
        operand = evaluate_stmt(node.operand, env)
        # Vérifie le type pour l'opérateur 'not'
        _check_valid_piandor_type(operand)
        return VBool(not operand.value) # type: ignore

    elif isinstance(node, PiAnd):
        left = evaluate_stmt(node.left, env)
        _check_valid_piandor_type(left)
        if not left.value: # type: ignore
            return left
        right = evaluate_stmt(node.right, env)
        _check_valid_piandor_type(right)
        return right

    elif isinstance(node, PiOr):
        left = evaluate_stmt(node.left, env)
        _check_valid_piandor_type(left)
        if left.value: # type: ignore
            return left
        right = evaluate_stmt(node.right, env)
        _check_valid_piandor_type(right)
        return right

    elif isinstance(node, PiWhile):
        return _evaluate_while(node, env)
   
    elif isinstance(node, PiFunctionDef):
        closure = VFunctionClosure(node, env)
        insert(env, node.name, closure)
        return VNone(value=None)

    elif isinstance(node, PiReturn):
        value = evaluate_stmt(node.value, env)
        raise ReturnException(value)

    elif isinstance(node, PiFunctionCall):
        return _evaluate_function_call(node, env)

    elif isinstance(node, PiFor):
        return _evaluate_for(node, env)

    elif isinstance(node, PiBreak):
        raise BreakException()

    elif isinstance(node, PiContinue):
        raise ContinueException()

    elif isinstance(node, PiIn):
        return _evaluate_in(node, env)

    elif isinstance(node, PiSubscript):
        return _evaluate_subscript(node, env)

    else:
        raise TypeError(f"Type de nœud non supporté : {type(node)}")

def _check_valid_piandor_type(obj):
    """Vérifie que le type est valide pour 'and'/'or'."""
    if not isinstance(obj, VBool | VNumber | VString | VNone | VList | VTuple):
        raise TypeError(f"Type non supporté pour l'opérateur 'and': {type(obj).__name__}")

def _evaluate_while(node: PiWhile, env: EnvFrame) -> EnvValue:
    """Évalue une boucle while."""
    last_value = VNone(value=None)
    while True:
        cond = evaluate_stmt(node.condition, env)
        cond = check_type(cond, VBool)
        if not cond.value:
            break
        try:
            last_value = evaluate(node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return last_value

def _evaluate_for(node: PiFor, env: EnvFrame) -> EnvValue:
    """Évalue une boucle for."""
    iterable_val = evaluate_stmt(node.iterable, env)
    if not isinstance(iterable_val, (VList, VTuple)):
        raise TypeError("La boucle for attend une liste ou un tuple.")
    last_value = VNone(value=None)
    iterable = iterable_val.value
    for item in iterable:
        env.insert(node.var, item)  # Pas de nouvel environnement pour la variable de boucle
        try:
            last_value = evaluate(node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return last_value

def _evaluate_subscript(node: PiSubscript, env: EnvFrame) -> EnvValue:
    """Évalue une opération d'indexation (subscript)."""
    collection = evaluate_stmt(node.collection, env)
    index = evaluate_stmt(node.index, env)
    # Indexation pour liste, tuple ou chaîne
    if isinstance(collection, VList):
        idx = check_type(index, VNumber)
        return collection.value[int(idx.value)]
    elif isinstance(collection, VTuple):
        idx = check_type(index, VNumber)
        return collection.value[int(idx.value)]
    elif isinstance(collection, VString):
        idx = check_type(index, VNumber)
        return VString(collection.value[int(idx.value)])
    else:
        raise TypeError("L'indexation n'est supportée que pour les listes, tuples et chaînes.")

def _evaluate_in(node: PiIn, env: EnvFrame) -> EnvValue:
    """Évalue l'opérateur 'in'."""
    container = evaluate_stmt(node.container, env)
    element = evaluate_stmt(node.element, env)
    if isinstance(container, (VList, VTuple)):
        return VBool(element in container.value)
    elif isinstance(container, VString):
        if isinstance(element, VString):
            return VBool(element.value in container.value)
        else:
            return VBool(False)
    else:
        raise TypeError("'in' n'est supporté que pour les listes et chaînes.")
    

def _evaluate_function_call(node: PiFunctionCall, env: EnvFrame) -> EnvValue:
    """Évalue un appel de fonction en gérant correctement le self des méthodes."""
    func_val = evaluate_stmt(node.function, env)
    args = [evaluate_stmt(arg, env) for arg in node.args]

    # Fonctions primitives
    if callable(func_val):
        return func_val(args)

    # Méthodes (VMethodClosure)
    if isinstance(func_val, VMethodClosure):
        # On ajoute automatiquement self comme premier argument
        args = [func_val.instance] + args
        func_val = func_val.function

    # Construction d'objet (appel de classe)
    if isinstance(func_val, VClassDef):
        obj = VObject(func_val, {})
        # Si la classe a une méthode __init__, on l'appelle
        if '__init__' in func_val.methods:
            init_method = func_val.methods['__init__']
            # On appelle __init__ avec l'objet comme self + les autres arguments
            _call_method(init_method, obj, args, env)
        return obj

    #  Fonctions utilisateur normales
    if isinstance(func_val, VFunctionClosure):
        return _call_function(func_val, args, env)

    raise TypeError(f"'{type(func_val).__name__}' n'est pas callable ou n'est pas une fonction valide.")

def _call_method(method: VFunctionClosure, instance: VObject, args: list[EnvValue], env: EnvFrame) -> EnvValue:
    """Appelle une méthode avec son instance comme self."""
    call_env = EnvFrame(parent=method.closure_env)
    # On s'assure que le premier paramètre est bien 'self'
    method.funcdef.arg_names[0] = 'self'
    call_env.insert('self', instance)
    
    # Gestion des autres arguments
    for i, arg_name in enumerate(method.funcdef.arg_names[1:], start=1):
        if i < len(args) + 1:  # +1 car on a déjà mis self
            call_env.insert(arg_name, args[i-1])
        else:
            raise TypeError(f"Argument manquant '{arg_name}' pour la méthode '{method.funcdef.name}'")

    # Exécution
    result = VNone(value=None)
    try:
        for stmt in method.funcdef.body:
            result = evaluate_stmt(stmt, call_env)
    except ReturnException:
        pass  # __init__ ne doit pas retourner de valeur
    return result

def _call_function(func: VFunctionClosure, args: list[EnvValue], env: EnvFrame) -> EnvValue:
    """Appelle une fonction normale avec gestion des arguments variables (*rest)."""
    call_env = EnvFrame(parent=func.closure_env)
    funcdef = func.funcdef
    
    # Nombre d'arguments normaux attendus
    normal_arg_count = len(funcdef.arg_names)
    
    # Assigner les arguments positionnels
    for i, arg_name in enumerate(funcdef.arg_names):
        if i < len(args):
            call_env.insert(arg_name, args[i])
        else:
            raise TypeError(f"Argument manquant '{arg_name}' pour la fonction '{funcdef.name}'")

    # Gérer les arguments variables (*rest) s'ils existent
    if funcdef.vararg:
        # Récupère les arguments supplémentaires
        rest_args = args[normal_arg_count:]
        # Les stocke dans une VList sous le nom du paramètre vararg
        call_env.insert(funcdef.vararg, VList(rest_args))
    elif len(args) > normal_arg_count:
        raise TypeError(f"Trop d'arguments pour la fonction '{funcdef.name}' (attendus {normal_arg_count}, reçus {len(args)})")

    # Exécution du corps de la fonction
    result = VNone(value=None)
    try:
        for stmt in funcdef.body:
            result = evaluate_stmt(stmt, call_env)
    except ReturnException as ret:
        return ret.value
    return result


def _evaluate_class_def(node: PiClassDef, env: EnvFrame) -> EnvValue:
    """Évalue une définition de classe."""
    # Crée un nouvel environnement pour la classe
    class_env = EnvFrame(parent=env)
    
    # Évalue les méthodes et les stocke dans un dictionnaire
    methods = {}
    for method_def in node.methods:
        method_closure = VFunctionClosure(method_def, class_env)
        methods[method_def.name] = method_closure
    
    # Crée la définition de classe
    class_def = VClassDef(node.name, methods)
    
    # Enregistre la classe dans l'environnement courant
    insert(env, node.name, class_def)
    return VNone(value=None)


def _evaluate_attribute(node: PiAttribute, env: EnvFrame) -> EnvValue:
    """Évalue un accès à un attribut (obj.attr) en gérant:
    - Les attributs d'instance
    - Les méthodes d'instance
    - Les méthodes de classe
    """
    obj = evaluate_stmt(node.object, env)
    
    # Si c'est un objet (instance de classe)
    if isinstance(obj, VObject):
        # D'abord vérifier les attributs d'instance
        if node.attr in obj.attributes:
            return obj.attributes[node.attr]
        
        # Ensuite vérifier les méthodes de classe
        if node.attr in obj.class_def.methods:
            method_closure = obj.class_def.methods[node.attr]
            return VMethodClosure(method_closure, obj)  # Lie la méthode à l'instance

        raise AttributeError(f"'{obj.class_def.name}' l'objet n'a pas d'attribut '{node.attr}'")

    # Si c'est une classe (accès à une méthode de classe)
    elif isinstance(obj, VClassDef):
        if node.attr in obj.methods:
            return obj.methods[node.attr]  # Retourne directement la closure (sans instance)

        raise AttributeError(f"Class '{obj.name}' n'a pas d'attribut '{node.attr}'")

    # Erreur pour les autres types
    else:
        raise TypeError(f"accès à un attribut sur un type qui n'est ni une classe ni un objet : {type(obj).__name__}")    

def _evaluate_attribute_assignment(node: PiAttributeAssignment, env: EnvFrame) -> EnvValue:
    """Évalue une affectation d'attribut."""
    obj = evaluate_stmt(node.object, env)
    value = evaluate_stmt(node.value, env)
    
    if isinstance(obj, VObject):
        # Affectation d'un attribut d'instance
        obj.attributes[node.attr] = value
        return value
    else:
        raise TypeError("L'affectation d'attribut n'est possible que sur les objets")

class ReturnException(Exception):
    """Exception pour retourner une valeur depuis une fonction."""
    def __init__(self, value):
        self.value = value

class BreakException(Exception):
    """Exception pour sortir d'une boucle (break)."""
    pass

class ContinueException(Exception):
    """Exception pour passer à l'itération suivante (continue)."""
    pass
