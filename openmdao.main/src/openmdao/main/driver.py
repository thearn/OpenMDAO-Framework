#public symbols
__all__ = ["Driver"]

__version__ = "0.1"


from zope.interface import implements
import networkx as nx
from networkx.algorithms.traversal import strongly_connected_components

from openmdao.main.interfaces import IDriver, IComponent, IAssembly
from openmdao.main.component import Component, STATE_WAITING, STATE_IDLE
from openmdao.main import Assembly, RefVariable, RefVariableArray
from openmdao.main.variable import INPUT, OUTPUT


class Driver(Assembly):
    """ A Driver iterates over a collection of Components until some condition
    is met. """
    
    implements(IDriver)

    def __init__(self, name, parent=None, doc=None):
        super(Driver, self).__init__(name, parent, doc=doc)
        self._ref_graph = None
        self._sorted_comps = None
        
    def _pre_execute (self):
        """Call base class _pre_execute after determining if we have any invalid
        ref variables, which will cause us to have to regenerate our ref dependency graph.
        """
        invalid_refs = [v for v in self.get_inputs(valid=False) if isinstance(v,RefVariable) or
                                                                   isinstance(v,RefVariableArray)]
        if len(invalid_refs) > 0:
            self._ref_graph = None  # force regeneration of ref graph
            
        super(Driver, self)._pre_execute()
                
    def execute(self):
        """ Iterate over a collection of Components until some condition
        is met. """
        self.state = STATE_WAITING
        self.start_iteration()
        while self.continue_iteration():
            self.pre_iteration()
            self.run_iteration()
            self.post_iteration()
        self.state = STATE_IDLE

    def step(self):
        """Execute a single step"""
        return self.parent.workflow.step()
        
    def stop(self):
        """ Stop the Model by stopping the Workflow. """
        self._stop = True
        self.parent.workflow.stop()
    
    def start_iteration(self):
        """Called just prior to the beginning of an iteration loop. This can 
        be overridden by inherited classes. It can be used to perform any 
        necessary pre-iteration initialization.
        """
        self._continue = True

    def continue_iteration(self):
        """Return False to stop iterating."""
        return self._continue
    
    def pre_iteration(self):
        """Called prior to each iteration."""
        pass
        
    def run_iteration(self):
        """Run a single iteration over a group of Components. This is generally
        overridden in derived classes."""
        if self.parent:
            self.parent.workflow.run()

    def post_iteration(self):
        """Called after each iteration."""
        self._continue = False
    
    def get_referenced_comps(self, iostatus=None):
        """Return a set of names of Components that we reference based on the 
        contents of our RefVariables and RefVariableArrays.  If iostatus is
        supplied, return only component names that are referenced by ref
        variables with matching iostatus.
        """
        comps = set()
        if iostatus is None:
            for refin in [v for v in self._pub.values() if (isinstance(v,RefVariable) or 
                                                   isinstance(v,RefVariableArray))]:
                comps.update(refin.get_referenced_compnames())
        else:
            for refin in [v for v in self._pub.values() if (isinstance(v,RefVariable) or 
                                                   isinstance(v,RefVariableArray))
                                               and v.iostatus==iostatus]:
                comps.update(refin.get_referenced_compnames())
        return comps
        
    def get_ref_graph(self, skip_inputs=False):
        """Returns the dependency graph for this Driver based on
        RefVariables and RefVariableArrays.
        """
        self._ref_graph = nx.DiGraph()
        for refout in self.get_referenced_comps(iostatus=OUTPUT):
            self._ref_graph.add_edge(self.name, refout)
        if not skip_inputs:
            for refin in self.get_referenced_comps(iostatus=INPUT):
                self._ref_graph.add_edge(refin, self.name)

        return self._ref_graph
    
    def sorted_components(self):
        """Return the names of our referenced components, sorted in dataflow order.
        """
        if self.parent and IAssembly.providedBy(self.parent):
            nbunch = self.get_referenced_comps()
            graph = self.parent.get_component_graph().subgraph(nbunch=nbunch)
            graph.add_edges_from(self.get_ref_graph(skip_inputs=True).edges())
            self._sorted_comps = nx.topological_sort(graph)
            if self._sorted_comps is None:
                for strcon in strongly_connected_components(graph):
                    if len(strcon) > 1:
                        self.raise_exception('subgraph for driver %s has a cycle (%s)' %
                                     (self.get_pathname(), str(strcon)), RuntimeError) 
        else:
            self.raise_exception('Driver requires an Assembly parent to determine dataflow', 
                                 RuntimeError)
        return self._sorted_comps
    
    def run_referenced_comps(self):
        """Runs the set of components that we reference via our reference variables."""
        if self.parent:
            for compname in self.sorted_components():
                if compname != self.name:
                    getattr(self.parent, compname).run()
        else:
            self.raise_exception('Driver cannot run referenced components without a parent',
                                 RuntimeError)

            