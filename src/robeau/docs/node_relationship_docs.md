
# Node Relationship and Activation Documentation

### ALLOWS
Allows are an inactive relationship only here to signal the fact that robeau must be greeted before we utter prompts, but the logic for that is handled in the robeau module, it does not rely on the graph_logic_network. It is also simply there for the database to arrange the nodes around the "hey robeau" single centralized node, to make it pretty.

## Activations

### CHECKS
First relation in priority, will always execute unless blocked.

### ATTEMPTS
Second in order, will only trigger if the node has been explicitly unlocked. (Note: Unlocking does not unlock locks, it simply allows a node to be attempted. Locking a node prevents it from being reached.)

### TRIGGERS
Simple trigger, will execute unless the node is blocked.

### DEFAULTS
Last in order, will only trigger if all other activations failed.

All these relationships may have a random weight and be pooled into explicitly stated different groups. In those cases, we select one random connection from pool 1, then 2, etc., as many pools as there are. If none are specified, all are in the same default pool.

## Definitions

### LOCKS
Prevents a node from being triggered.

### UNLOCKS
Allows a node to be attempted.

### EXPECTS
Will reduce the scope of conversation to the expected nodes. If none are reached, it will warn the user, then try again. If it fails again, Robeau will give up and move on. There's a time delay on expects so that you don't leave Robeau hanging for like 10 seconds after he asked a question. The way this is communicated to the database is by using additional node processing when the condition is raised in the `ConversationState` class, only this time using SYSTEM as a source rather than USER/ROBEAU.

### LISTENS
Kind of a silent expect. The scope won't be reduced, but some answers that were not accessible will now be recognized under the Whisper label. If anything other than the whisper is said, it just proceeds as normal. Listens usually have a time limitation.

### PRIMES
Like unlock, only it will get deactivated as soon as any activation relation is successful, so it's a one-time thing.

### INITIATES
After a time countdown, will activate the node.

## Modifications

### DISABLES
Will remove conditions `initiate` and `primes`. (All definitions can be implemented to be disabled very easily, but for now, we keep it like that.)

### DELAYS
Unused right now, but the principle is to allow adding time to any condition, as long as it exists. We don't use it right now because simply re-applying the condition also works and will work whether the condition already exists or not.

### REVERTS
Will undo the changes a node had applied to its target nodes with its relationships. For example, if it locked something, it de-locks it; if it had unlocked one, it de-unlocks it, etc.

## Logics Checks

### IF
Will gather all connections of the target logic gate node and resolve them to be either true or false. It will then trigger or not accordingly the "then" relationship if the gate is true, activating another nodes.

## Logics Relationships

### IS_ATTRIBUTE
Will check if the attribute is being kept track off in the `ConversationState` class (locks, unlocks, etc.).

### AND_IS_ATTRIBUTE
Will check if all the attributes connected are being kept track off (including the original one: IS_ATTRIBUTE).