"""Week 4 Analytics Demo.

Demonstrates the complete Week 4 analytics pipeline:
1. Load a Week 3 discussion
2. Run unified analytics (opinion, agreement, influence, sentiment)
3. Generate a Markdown report
4. Create visualizations (opinion trajectory chart, interaction graph)
"""

import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Run the Week 4 analytics demonstration."""
    print("=" * 60)
    print("Week 4 Analytics & Intelligence Layer Demo")
    print("=" * 60)

    try:
        # Import Week 4 components
        from src.analytics.unified import analyze_discussion, analyze_discussion_to_dict
        from src.reporting.report_generator import generate_report
        from src.visualization.visualizer import create_opinion_trajectory_chart, create_interaction_graph

        print("✓ Successfully imported Week 4 modules")

    except ImportError as e:
        print(f"✗ Failed to import Week 4 modules: {e}")
        print("Make sure you're running this from the project root directory")
        return 1

    # Try to load a sample discussion from Week 3
    discussion_id = "test-run-001"  # This should exist in data/discussions/
    discussion_path = f"data/discussions/{discussion_id}.json"

    if not os.path.exists(discussion_path):
        print(f"⚠ Discussion file not found: {discussion_path}")
        print("Creating a minimal demo discussion for testing purposes...")

        # Create a minimal discussion for demo purposes
        discussion_state = create_demo_discussion()
    else:
        try:
            from src.persistence.file_persistence import FilePersistence
            store = FilePersistence()
            discussion_state = store.load(discussion_id)
            if discussion_state is None:
                print(f"⚠ Failed to load discussion {discussion_id}")
                print("Creating a minimal demo discussion for testing purposes...")
                discussion_state = create_demo_discussion()
            else:
                print(f"✓ Loaded discussion: {discussion_state.discussion_id}")
                print(f"  Topic: {discussion_state.topic}")
                print(f"  Rounds: {len(set(msg.round for msg in discussion_state.messages))}")
                print(f"  Agents: {len(set(op.agent_id for ops in discussion_state.opinions.values() for op in ops))}")
        except Exception as e:
            print(f"⚠ Error loading discussion: {e}")
            print("Creating a minimal demo discussion for testing purposes...")
            discussion_state = create_demo_discussion()

    # Run unified analytics
    print("\n" + "-" * 50)
    print("Running Unified Analytics...")
    print("-" * 50)

    try:
        analytics_results = analyze_discussion_to_dict(discussion_state)
        print("✓ Unified analytics completed successfully")

        # Show brief summary of what was computed
        opinion_count = len(analytics_results.get('opinion_change', {})) if isinstance(analytics_results.get('opinion_change'), dict) else 0
        agreement_count = len(analytics_results.get('agreement', [])) if isinstance(analytics_results.get('agreement'), list) else 0
        influence_count = len(analytics_results.get('influence', {})) if isinstance(analytics_results.get('influence'), dict) else 0
        sentiment_count = len(analytics_results.get('sentiment', [])) if isinstance(analytics_results.get('sentiment'), list) else 0

        print(f"  - Opinion change trajectories: {opinion_count} agents")
        print(f"  - Agreement scores: {agreement_count} rounds")
        print(f"  - Influence scores: {influence_count} agents")
        print(f"  - Sentiment analyses: {sentiment_count} messages")

    except Exception as e:
        print(f"✗ Error during analytics computation: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Generate report
    print("\n" + "-" * 50)
    print("Generating Report...")
    print("-" * 50)

    try:
        report_path = generate_report(
            analytics_results=analytics_results,
            discussion_id=getattr(discussion_state, 'discussion_id', 'demo'),
            topic=getattr(discussion_state, 'topic', 'Demo Topic'),
            output_path="reports/demo_discussion_report.md"
        )
        print(f"✓ Report generated: {report_path}")

        # Show first few lines of the report
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print("  Report preview:")
                for i, line in enumerate(lines[:10]):  # Show first 10 lines
                    print(f"    {line.rstrip()}")
                if len(lines) > 10:
                    print("    ...")

    except Exception as e:
        print(f"✗ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Create visualizations
    print("\n" + "-" * 50)
    print("Creating Visualizations...")
    print("-" * 50)

    try:
        # Opinion trajectory chart
        opinion_chart_path = create_opinion_trajectory_chart(
            opinion_change_data=analytics_results.get('opinion_change', {}),
            output_path="reports/opinion_trajectory.png"
        )
        if opinion_chart_path:
            print(f"✓ Opinion trajectory chart: {opinion_chart_path}")
        else:
            print("⚠ Opinion trajectory chart generation failed (possibly missing matplotlib)")

        # Interaction graph
        interaction_graph_path = create_interaction_graph(
            influence_data=analytics_results.get('influence', {}),
            output_path="reports/interaction_graph.png"
        )
        if interaction_graph_path:
            print(f"✓ Interaction graph: {interaction_graph_path}")
        else:
            print("⚠ Interaction graph generation failed (possibly missing matplotlib)")

    except Exception as e:
        print(f"✗ Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("Week 4 Analytics Demo Completed Successfully!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - reports/demo_discussion_report.md")
    print("  - reports/opinion_trajectory.png (if matplotlib available)")
    print("  - reports/interaction_graph.png (if matplotlib available)")
    print("\nNext steps for Week 5:")
    print("  - The dashboard can load the generated report and visualizations")
    print("  - Analytics engine provides unified interface for all four metric categories")

    return 0


def create_demo_discussion():
    """Create a minimal discussion for demonstration purposes."""
    from src.orchestration.models import DiscussionState, DiscussionStatus, Message, OpinionRecord

    discussion_state = DiscussionState(
        discussion_id="demo-week4-run",
        topic="Should developed countries increase climate finance?",
        status=DiscussionStatus.COMPLETED,
        participants=["investor", "policy_expert", "scientist", "cfo_agent"],
        current_round=2,
        total_rounds=2
    )

    discussion_state.add_message(Message(
        message_id="msg_001",
        discussion_id="demo-week4-run",
        round=0,
        agent_id="investor",
        agent_name="Climate Investor",
        content="I believe we should significantly increase climate finance to support renewable energy projects in developing countries."
    ))

    discussion_state.add_message(Message(
        message_id="msg_002",
        discussion_id="demo-week4-run",
        round=0,
        agent_id="policy_expert",
        agent_name="Policy Expert",
        content="While I agree on the importance, we need to ensure proper governance and accountability mechanisms are in place."
    ))

    discussion_state.add_message(Message(
        message_id="msg_003",
        discussion_id="demo-week4-run",
        round=1,
        agent_id="scientist",
        agent_name="Environmental Scientist",
        content="The science is clear: urgent action is needed. Increased finance is critical for mitigation and adaptation efforts."
    ))

    discussion_state.add_message(Message(
        message_id="msg_004",
        discussion_id="demo-week4-run",
        round=1,
        agent_id="cfo_agent",
        agent_name="CFO Agent",
        content="From a financial perspective, we need to carefully evaluate the ROI and risks associated with large-scale climate finance initiatives."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="investor",
        agent_name="Climate Investor",
        round=0,
        opinion="We should significantly increase climate finance to support renewable energy projects."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="investor",
        agent_name="Climate Investor",
        round=1,
        opinion="After considering the risks, I believe a moderate increase in climate finance is warranted."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="policy_expert",
        agent_name="Policy Expert",
        round=0,
        opinion="We need to ensure proper governance and accountability mechanisms are in place before increasing finance."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="policy_expert",
        agent_name="Policy Expert",
        round=1,
        opinion="With proper safeguards in place, I support increasing climate finance for adaptation projects."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="scientist",
        agent_name="Environmental Scientist",
        round=0,
        opinion="The science is clear: urgent action is needed on climate change."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="scientist",
        agent_name="Environmental Scientist",
        round=1,
        opinion="Increased finance is critical for both mitigation and adaptation efforts to address the climate crisis."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="cfo_agent",
        agent_name="CFO Agent",
        round=0,
        opinion="We need to carefully evaluate the ROI and risks associated with large-scale climate finance initiatives."
    ))

    discussion_state.add_opinion(OpinionRecord(
        agent_id="cfo_agent",
        agent_name="CFO Agent",
        round=1,
        opinion="While there are risks, the long-term benefits of climate action justify moderate increases in climate finance."
    ))

    return discussion_state


if __name__ == "__main__":
    sys.exit(main())