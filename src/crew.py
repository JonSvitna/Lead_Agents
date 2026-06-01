from lead_agents.crew import build_crew, kickoff


def main() -> None:
    kickoff({"query": "Maryland defense subcontractor MSP", "limit": 5})


if __name__ == "__main__":
    main()
