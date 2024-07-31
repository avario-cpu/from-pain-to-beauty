from src.robeau.jsons.modules.submodules import (
    neo4j_all_data_getter,
    neo4j_prompts_getter,
    neo4j_prompts_merger,
    neo4j_responses_getter,
    neo4j_responses_merger,
)


def run_all():
    print("Running neo4j_all_data_getter...")
    neo4j_all_data_getter.main()

    print("Running neo4j_prompts_getter...")
    neo4j_prompts_getter.main()

    print("Running neo4j_prompts_merger...")
    neo4j_prompts_merger.main()

    print("Running neo4j_responses_getter...")
    neo4j_responses_getter.main()

    print("Running neo4j_responses_merger...")
    neo4j_responses_merger.main()


if __name__ == "__main__":
    run_all()
