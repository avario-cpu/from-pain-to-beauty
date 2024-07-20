# conversation_state.py
from logging import Logger
import time
from neo4j import Session


class ConversationState:
    def __init__(self, logger: Logger):
        self.logger = logger
        # definitions items
        self.allows: list[dict] = []
        self.locks: list[dict] = []
        self.unlocks: list[dict] = []
        self.expectations: list[dict] = []
        self.primes: list[dict] = []
        self.listens: list[dict] = []
        # activations items
        self.initiations: list[dict] = []

    def set_process_node_func(self, process_node_func):
        self.process_node = process_node_func

    def set_get_node_connections_func(self, get_node_connections_func):
        self.get_node_connections = get_node_connections_func

    def set_activate_node_func(self, activate_node_func):
        self.activate_node = activate_node_func

    def set_query_sources_params(self, ROBEAU_param, REVERTER_param):
        self.ROBEAU = ROBEAU_param
        self.REVERTER = REVERTER_param

    def _add_item(
        self, node: str, duration: float | None, item_list: list, item_type: str
    ):
        start_time = time.time()

        for existing_item in item_list:
            if existing_item["node"] == node:
                if duration is None:  # None means infinite duration here
                    return

                # Refresh duration if the item already exists
                existing_item["duration"] = duration
                existing_item["timeLeft"] = duration
                existing_item["start_time"] = start_time
                self.logger.info(f"Refreshed the time duration of {existing_item}")
                return

        item_list.append(
            {
                "type": item_type,
                "node": node,
                "timeLeft": duration,
                "duration": duration,
                "start_time": start_time,
            }
        )

    def add_allow(self, node: str, duration: float | None):
        self._add_item(node, duration, self.allows, "allow")

    def add_unlock(self, node: str, duration: float | None):
        self._add_item(node, duration, self.unlocks, "unlock")

    def add_lock(self, node: str, duration: float | None):
        self._add_item(node, duration, self.locks, "lock")

    def add_expectation(self, node: str, duration: float | None):
        self._add_item(node, duration, self.expectations, "expectation")

    def add_prime(self, node: str, duration: float | None):
        self._add_item(node, duration, self.primes, "prime")

    def add_listens(self, node: str, duration: float | None):
        self._add_item(node, duration, self.listens, "listen")

    def add_initiation(self, node: str, duration: float | None):
        self._add_item(node, duration, self.initiations, "initiation")

    def delay_item(self, node: str, duration: float | None):
        """Unused right now but may be used in the future, Logic wise just know that the difference between this and add_initiation is that this is for items that are already in the conversation state, which means a previously processed node wont be processed again if they are pointed to with a DELAY relationship"""
        for node_list in [self.locks, self.unlocks, self.expectations, self.primes]:
            for item in node_list:
                if item["node"] == node:
                    self._add_item(node, duration, node_list, item["type"])

    def disable_item(self, node: str):
        for node_list in [self.primes, self.initiations, self.listens]:
            for item in node_list:
                if item["node"] == node:
                    node_list.remove(item)
                    self.logger.info(f"Item disabled: {item}")
                    return

    def _update_time_left(self, item: dict):
        current_time = time.time()
        start_time = item["start_time"]
        duration = item["duration"]
        time_left = item.get("timeLeft")

        if time_left is not None:
            elapsed_time = current_time - start_time
            remaining_time = max(0, duration - elapsed_time)
            item["timeLeft"] = remaining_time

    def _remove_expired(self, items: list, log_messages: list) -> list:
        valid_items = []

        for item in items:
            self._update_time_left(item)
            time_left = item.get("timeLeft")
            if time_left is None or time_left > 0:
                valid_items.append(item)
                if time_left is not None:
                    log_messages.append(f"{item}")
            else:
                self.logger.info(f"Item has expired: {item}")

        return valid_items

    def _check_initiations(self, session: "Session", log_messages: list):
        ongoing_initiations = []
        complete_initiations = []

        for initiation in self.initiations:
            self._update_time_left(initiation)
            time_left = initiation.get("timeLeft")

            if time_left is None:
                raise ValueError(
                    f"Initiation has invalid duration {time_left}: {initiation}"
                )

            if time_left > 0:
                ongoing_initiations.append(initiation)
                log_messages.append(f"{initiation}")
            else:
                self.logger.info(f"Initiation complete: {initiation}")
                complete_initiations.append(initiation)

        self.initiations = ongoing_initiations

        for initiation in complete_initiations:
            self.activate_node(initiation)
            self.process_node(session, initiation["node"], self, source=self.ROBEAU)

    def update_timed_items(self, session: "Session"):
        items_to_update = [
            "allows",
            "locks",
            "unlocks",
            "expectations",
            "primes",
            "listens",
        ]
        log_messages: list[str] = []

        for item in items_to_update:
            updated_items = self._remove_expired(getattr(self, item), log_messages)
            setattr(self, item, updated_items)

        self._check_initiations(session, log_messages)

        if log_messages:
            self.logger.info(
                "Time-bound items update:\n" + "\n".join(log_messages) + "\n"
            )

    def reset_attribute(self, attribute: str):
        valid_attributes = [
            "locks",
            "unlocks",
            "primes",
            "expectations",
            "listens",
            "initiations",
        ]

        if attribute in valid_attributes:
            if getattr(self, attribute, None):
                setattr(self, attribute, [])
                self.logger.info(f'Reset attribute: "{attribute}"')
        else:
            self.logger.error(f'Invalid attribute: "{attribute}"')

    def revert_definitions(self, session: Session, node: str):
        """Reverts the locks and unlock which the target node had instilled on other nodes"""
        definitions_to_revert = (
            self.get_node_connections(
                session=session,
                text=node,
                source=self.REVERTER,
                conversation_state=self,
            )
            or []
        )
        formatted_definitions = [
            (i["start_node"], i["relationship"], i["end_node"])
            for i in definitions_to_revert
        ]
        self.logger.info(f"Obtained definitions to revert: {formatted_definitions}")

        for connection in definitions_to_revert:
            end_node = connection.get("end_node", "")

            self._revert_individual_definition("lock", end_node, self.locks)
            self._revert_individual_definition("unlock", end_node, self.unlocks)
            self._revert_individual_definition("allow", end_node, self.allows)

    def _revert_individual_definition(
        self, definition_type: str, node: str, definitions: list[dict]
    ):
        initial_count = len(definitions)
        definitions[:] = [
            definition for definition in definitions if definition["node"] != node
        ]
        if len(definitions) < initial_count:
            self.logger.info(f'Removed {definition_type} for: "{node}"')

    def log_conversation_state(self):
        state_types = {
            "Allow": self.allows,
            "Lock": self.locks,
            "Unlock": self.unlocks,
            "Expectation": self.expectations,
            "Prime": self.primes,
            "Listen": self.listens,
            "Initiation": self.initiations,
        }

        log_message = []

        if any(state_types.values()):
            log_message.append("Conversation state:")
            for state_name, items in state_types.items():
                for item in items:
                    log_message.append(f"{state_name}: {item}")
        else:
            log_message.append("No items in conversation state")

        self.logger.info("\n".join(log_message) + "\n")
