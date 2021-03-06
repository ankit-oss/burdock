from typing import List, Any, Dict, Union
import itertools

class Token(str):
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text
    def __eq__(self, other):
        if isinstance(other, str):
            return self.text == other
        return type(self) == type(other) and self.text == other.text
    def children(self):
        return [None]
    def __hash__(self):
        return hash(self.text)

class Op(str):
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text
    def __eq__(self, other):
        if isinstance(other, str):
            return self.text == other
        return type(self) == type(other) and self.text == other.text
    def children(self):
        return [None]
    def __hash__(self):
        return hash(self.text)

class Identifier(str):
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text
    def __eq__(self, other):
        if isinstance(other, str):
            return self.text == other
        return type(self) == type(other) and self.text == other.text
    def children(self):
        return [None]
    def __hash__(self):
        return hash(self.text)

class FuncName(str):
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text
    def __eq__(self, other):
        if isinstance(other, str):
            return self.text == other
        return type(self) == type(other) and self.text == other.text
    def children(self):
        return [None]
    def __hash__(self):
        return hash(self.text)

"""
    base type for all Sql AST nodes
"""
class Sql:
    def __str__(self):
        return " ".join([str(c) for c in self.children() if c is not None])
    def __eq__(self, other):
        return all([s == o for s, o in zip(self.children(), other.children())])
    def symbol_name(self):
        return str(hex(hash(self) % (2**16)))
    def __hash__(self):
        return hash(tuple(self.children()))
    def children(self):
        return []

    """
        Walks the tree and returns the first node
        that is an instance of the specified type.
    """
    def find_node(self, type_name):
        candidates = [c for c in self.children() if c is not None]
        for c in candidates:
            if isinstance(c, type_name):
                return c
            if isinstance(c, Sql):
                n = c.find_node(type_name)
                if n is not None:
                    return n
        return None

    """
        Walks the tree and returns all nodes
        that are an instance of the specified type.
    """
    def find_nodes(self, type_name, not_child_of=None):
        candidates = [c for c in self.children() if c is not None]
        nodes = [c for c in candidates if isinstance(c, type_name)]
        sqlnodes = [c for c in candidates if isinstance(c, Sql)]
        if not_child_of is not None:
            sqlnodes = [c for c in sqlnodes if not isinstance(c, not_child_of)]
        childnodes = [c.find_nodes(type_name, not_child_of) for c in sqlnodes]
        return nodes + flatten(childnodes)


class Seq(Sql):
    def __init__(self, seq):
        self.seq = seq
    def __str__(self):
        return ", ".join([str(c) for c in self.seq if c is not None])
    def __eq__(self, other):
        return all([s == o for s, o in zip(self.seq, other.seq)])
    def __len__(self):
        return len(self.seq)
    def __getitem__(self, key):
        return self.seq[key]
    def __setitem__(self, key, value):
        self.seq[key] = value
    def __iter__(self):
        return iter(self.seq)
    def children(self):
        return self.seq


"""
    base type for all SQL relations
"""
class SqlRel(Sql):
    def __init__(self):
        self.m_symbols = None
        self.m_sym_dict = None
    def has_symbols(self):
        if hasattr(self, 'm_symbols'):
            return self.m_symbols is not None
        return any([r.has_symbols() for r in self.relations()])
    def alias_match(self, name):
        orig_name = name
        alias, name = self.split_alias(name)
        if alias.strip() == "":
            return True
        if hasattr(self, 'alias'):
            if self.alias is None:
                return False
            else:
                return self.alias.lower() == alias.lower()
        else:
            return any([r.alias_match(orig_name) for r in self.relations()])
    def split_alias(self, name):
        parts = name.split(".")
        if len(parts) > 2:
            raise ValueError("Identifiers can have only two parts: " + name)
        elif len(parts) == 2:
            return (parts[0], parts[1])
        else:
            return ("", parts[0])
    def __contains__(self, key):
        if not self.has_symbols():
            return False
        if self.m_sym_dict is None:
            self.m_sym_dict = dict(self.m_symbols)
        return key in self.m_sym_dict
    def __getitem__(self, key):
        if not self.has_symbols():
            raise ValueError("No symbols loaded")
        if self.m_sym_dict is None:
            self.m_sym_dict = dict(self.m_symbols)
        return self.m_sym_dict[key]
    def load_symbols(self, metadata):
        for r in self.relations():
            r.load_symbols(metadata)
    def all_symbols(self, expression=None):
        if not self.has_symbols():
            raise ValueError("Cannot load symbols from a table with no metadata.  Check has_symbols, or use load_symbols with metadata first. " + str(self))
        else:
            return self.m_symbols
    def relations(self):
        return [r for r in self.children() if isinstance(r, SqlRel)]

"""
    Base type for all SQL expressions
"""
class SqlExpr(Sql):
    def symbol(self, relations):
        return self
    def type(self):
        return "unknown"
    def sensitivity(self):
        return None
    def evaluate(self, bindings):
        raise ValueError("We don't know how to evaluate " + str(self))
    def children(self):
        return [None]

class Literal(SqlExpr):
    """A literal used in an expression"""
    def __init__(self, value, text=None):
        if text is None:
            self.value = value
            if value is None:
                self.text = 'NULL'
            else:
                self.text = str(value)
        else:
            if not isinstance(text, str):
                self.value = text
                self.text = str(value)
            else:
                self.text = text
                self.value = value
    def __str__(self):
        return self.text
    def __eq__(self, other):
        return type(self) == type(other) and self.text == other.text
    def __hash__(self):
        return hash(self.text)
    def symbol(self, relations):
        return self
    def type(self):
        if isinstance(self.value, str):
            return "string"
        elif type(self.value) is float:
            return "float"
        elif type(self.value) is int:
            return "int"
        elif type(self.value) is bool:
            return "boolean"
        else:
            raise ValueError("Unknown literal type: " + str(type(self.value)))
    def evaluate(self, bindings):
        return self.value


def flatten(iter):
    return list(itertools.chain.from_iterable(iter))

def unique(iter):
    return list(set(iter))
