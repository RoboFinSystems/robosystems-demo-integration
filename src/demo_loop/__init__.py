"""Demo tenant loop — provision, load, connect, tear down.

Orchestrates throwaway demo tenants on a deployed RoboSystems environment:
provision a graph on the invoice-billed demo org, load a showcase episode
from the public robosystems repo's examples, print the graph's MCP URL for
Claude to sign into over OAuth, and tear the whole thing down when the demo
is over.
"""
