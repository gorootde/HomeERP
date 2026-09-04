/**
 * Optimistic tag add/remove for a `form.tags` array (used with TagChips).
 *
 * While creating a new entity (`getEntityId()` returns a falsy value), tags
 * only live in the local array — there's no id yet to attach them to, so a
 * throwaway id is used. Once the entity exists, add/remove call the API and
 * refresh `tags` from the server so ids/ordering stay authoritative.
 *
 * `getForm()` must return the *current* form state, not a snapshot — call
 * sites typically reassign their `form` variable wholesale (e.g. `form = {
 * ... }` when opening the modal for a different row), so a plain object
 * reference captured once would go stale.
 *
 * Params:
 *   getForm() — returns the current state object with a `tags` array
 *   getEntityId() — current entity's id, or a falsy value while new
 *   addFn(id, name), removeFn(id, name) — the resource's tag API calls
 *   fetchTags(id) — resolves the fresh tags array after a change
 */
export function useTags(getForm, { getEntityId, addFn, removeFn, fetchTags }) {
  async function addTag(name) {
    const id = getEntityId();
    const form = getForm();
    if (!id) {
      form.tags = [...form.tags, { id: Date.now(), name }];
      return;
    }
    await addFn(id, name);
    form.tags = await fetchTags(id);
  }

  async function removeTag(name) {
    const id = getEntityId();
    const form = getForm();
    if (!id) {
      form.tags = form.tags.filter((t) => t.name !== name);
      return;
    }
    await removeFn(id, name);
    form.tags = await fetchTags(id);
  }

  return { addTag, removeTag };
}
