"""LangGraph BaseStore adapter over GovernedMemoryClient (M1 remediation)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from langgraph.store.base import BaseStore, GetOp, Item, ListNamespacesOp, PutOp, SearchOp


class SibylGovernedStore(BaseStore):
    """Thin BaseStore wrapper — agents use governance, not raw Sibyl."""

    def __init__(self, governed: Any, *, default_agent_id: str = "planner") -> None:
        self._gov = governed
        self._default_agent_id = default_agent_id
        self._memory: dict[tuple[tuple[str, ...], str], Item] = {}

    def batch(self, ops: Iterable[Any]) -> list[Any]:
        results: list[Any] = []
        for op in ops:
            if isinstance(op, GetOp):
                results.append(self._get(op))
            elif isinstance(op, PutOp):
                self._put(op)
                results.append(None)
            elif isinstance(op, SearchOp):
                results.append(self._search(op))
            elif isinstance(op, ListNamespacesOp):
                results.append(self._list_namespaces(op))
            else:
                results.append(None)
        return results

    def _ns_key(self, namespace: tuple[str, ...], key: str) -> tuple[tuple[str, ...], str]:
        return (namespace, key)

    def _get(self, op: GetOp) -> Item | None:
        return self._memory.get(self._ns_key(op.namespace, op.key))

    def _put(self, op: PutOp) -> None:
        ns = self._ns_key(op.namespace, op.key)
        if op.value is None:
            self._memory.pop(ns, None)
            return
        kind = op.namespace[-1] if op.namespace else "memory"
        name = op.key
        agent_id = op.namespace[0] if op.namespace else self._default_agent_id
        body = op.value if isinstance(op.value, dict) else {"data": op.value}
        self._gov.set_entity(kind, name, body, agent_id=agent_id)
        self._memory[ns] = Item(
            namespace=op.namespace,
            key=op.key,
            value=op.value,
            created_at=op.value.get("created_at") if isinstance(op.value, dict) else None,
            updated_at=op.value.get("updated_at") if isinstance(op.value, dict) else None,
        )

    def _search(self, op: SearchOp) -> list[Item]:
        query = op.query or ""
        hits = self._gov.search_entities(query)
        items: list[Item] = []
        for hit in hits[: op.limit or 10]:
            ns = tuple(hit.get("category", "warm").split(":"))
            key = hit.get("name", "")
            body = hit.get("body", {})
            items.append(Item(namespace=ns, key=key, value=body))
        return items

    def _list_namespaces(self, op: ListNamespacesOp) -> list[tuple[str, ...]]:
        seen: set[tuple[str, ...]] = set()
        for ns, _ in self._memory:
            if op.match_conditions:
                matched = True
                for cond in op.match_conditions:
                    if cond.match_type == "prefix" and not ns[: len(cond.path)] == tuple(cond.path):
                        matched = False
                if not matched:
                    continue
            seen.add(ns)
        return sorted(seen)[: op.limit or 100]

    async def abatch(self, ops: Iterable[Any]) -> list[Any]:
        return self.batch(ops)
