// Friendly present-continuous phrasing for tool calls shown in the activity feed.
export const NARRATION = {
  validate: 'Checking the dialogue',
  summarize: 'Mapping the flow',
  read_node: 'Reading a node',
  get_facts: 'Looking up facts',
  get_schema: 'Reading the schema',
  scaffold_bot: 'Scaffolding the bot',
  build: 'Building from manifest',
  add_component: 'Adding a component',
  add_node: 'Adding a node',
  connect_components: 'Connecting components',
  add_intent: 'Adding an intent',
  add_variable: 'Adding a variable',
  add_kb: 'Adding a knowledge base',
  apply_mods: 'Applying edits',
  set_path: 'Editing',
  delete_path: 'Deleting',
  rewire_edge: 'Rewiring an edge',
  delete_edge: 'Deleting an edge',
  delete_node: 'Deleting a node',
  move_node: 'Moving a node',
  rename_node: 'Renaming a node',
  complete_component: 'Completing the component',
};

export const narrate = (name) => NARRATION[name] || String(name || '').replace(/_/g, ' ');
