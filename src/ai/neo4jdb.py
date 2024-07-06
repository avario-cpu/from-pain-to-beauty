from neo4j import GraphDatabase

from src.config.settings import NEO4J_USER, NEO4J_URI, NEO4J_PASSWORD

NEO4J_URI = NEO4J_URI
NEO4J_USER = NEO4J_USER
NEO4J_PASSWORD = NEO4J_PASSWORD


class GreetingDatabase:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_greeting(self, msg, responses):
        with self.driver.session() as session:
            # Check if the greeting already exists
            result = session.run("""
            MATCH (g:Greeting {text: $msg})
            RETURN g
            """, msg=msg)

            if result.single() is not None:
                print("Greeting already exists in the database.")
                return "Greeting already exists"

            # Add the greeting and its possible responses
            session.write_transaction(self._create_greeting_with_responses,
                                      msg, responses)
            print("Greeting and responses added successfully.")
            return "Greeting and responses added"

    @staticmethod
    def _create_greeting_with_responses(tx, msg, responses):
        # Create the greeting node
        tx.run("""
        CREATE (g:Greeting {text: $msg})
        """, msg=msg)

        # Create response nodes and relationships
        for response in responses:
            tx.run("""
            MATCH (g:Greeting {text: $msg})
            MERGE (r:Response {text: $response})
            CREATE (g)-[:TRIGGERS]->(r)
            """, msg=msg, response=response)


def main():
    db = GreetingDatabase(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    message = "Hello"
    responses = ["Hi there!", "Hello!", "Greetings!"]

    result = db.add_greeting(message, responses)
    print(result)

    db.close()


if __name__ == "__main__":
    main()
