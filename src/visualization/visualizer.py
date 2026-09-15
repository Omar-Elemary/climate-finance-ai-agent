"""Visualization components (Week 4).

Creates opinion trajectory charts and interaction graph visualizations
from analytics results.
"""

import logging
from typing import Any, Dict, List, Tuple, Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


def create_opinion_trajectory_chart(
    opinion_change_data: Dict[str, Any],
    output_path: str = "reports/opinion_trajectory.png",
    figsize: Tuple[int, int] = (10, 6)
) -> Optional[str]:
    """Create an opinion trajectory chart showing agent stances over discussion rounds.

    Args:
        opinion_change_data: Opinion change results from analytics engine
        output_path: Path where the PNG image should be saved
        figsize: Figure size (width, height) in inches

    Returns:
        Path to the generated image file, or None if visualization failed

    The chart shows:
    - X-axis: Discussion rounds
    - Y-axis: Agent stance (-1.0 to +1.0)
    - Lines: Each agent's stance trajectory over time
    - Stance interpretation: -1 = strongly against, 0 = neutral, +1 = strongly in favor
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("Cannot create opinion trajectory chart: matplotlib not available")
        return None

    logger.info("Creating opinion trajectory chart")

    # Extract trajectory data
    trajectories = _extract_trajectories_for_plotting(opinion_change_data)

    if not trajectories:
        logger.warning("No trajectory data available for opinion chart")
        return None

    # Create the plot
    plt.figure(figsize=figsize)

    # Set up the plot aesthetics
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=0.8)
    plt.axhline(y=1, color='green', linestyle='--', alpha=0.5, linewidth=0.8)
    plt.axhline(y=-1, color='red', linestyle='--', alpha=0.5, linewidth=0.8)

    # Plot each agent's trajectory
    colors = plt.cm.Set1(np.linspace(0, 1, len(trajectories)))

    for (agent_id, agent_name), points, color in zip(trajectories.keys(), trajectories.values(), colors):
        if not points or len(points) < 2:
            continue

        # Extract rounds and stances
        rounds = [p[0] for p in points]
        stances = [p[1] for p in points]

        # Plot line
        plt.plot(rounds, stances, marker='o', linewidth=2.5, markersize=6,
                label=f'{agent_name}', color=color)

        # Add agent name labels at the end of each line
        if rounds and stances:
            plt.annotate(agent_name,
                        xy=(rounds[-1], stances[-1]),
                        xytext=(5, 0),
                        textcoords='offset points',
                        fontsize=9,
                        fontweight='bold',
                        color=color)

    # Customize the plot
    plt.xlabel('Discussion Round', fontsize=12, fontweight='bold')
    plt.ylabel('Agent Stance', fontsize=12, fontweight='bold')
    plt.title('Opinion Trajectories: Agent Stance Evolution Over Discussion Rounds',
              fontsize=14, fontweight='bold', pad=20)

    # Set y-axis limits with some padding
    plt.ylim(-1.2, 1.2)

    # Add grid
    plt.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Add legend
    plt.legend(loc='best', frameon=True, fancybox=True, shadow=True)

    # Add stance interpretation text - moved to prevent overlap with x-label
    plt.figtext(0.02, 0.01,
                "Stance Interpretation: -1 = Strongly Against, 0 = Neutral, +1 = Strongly In Favor",
                fontsize=9, style='italic')

    # Adjust layout with more bottom space to prevent overlap
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  # Add more space at the bottom

    # Ensure output directory exists
    import os
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

    logger.info(f"Opinion trajectory chart saved to {output_path}")
    return output_path


def create_interaction_graph(
    influence_data: Dict[str, Any],
    message_activity_data: Optional[Dict] = None,
    output_path: str = "reports/interaction_graph.png",
    figsize: Tuple[int, int] = (10, 8)
) -> Optional[str]:
    """Create an interaction graph visualization showing agent relationships.

    Args:
        influence_data: Influence results from analytics engine
        message_activity_data: Optional message activity data for edge weights
        output_path: Path where the PNG image should be saved
        figsize: Figure size (width, height) in inches

    Returns:
        Path to the generated image file, or None if visualization failed

    The graph shows:
    - Nodes: Agents (sized by influence score)
    - Edges: Communication relationships (width by interaction strength)
    - Edge color: Based on interaction type (influence vs message volume)
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("Cannot create interaction graph: matplotlib not available")
        return None

    logger.info("Creating interaction graph")

    # Extract data for the graph
    nodes, edges = _extract_graph_data(influence_data, message_activity_data)

    if not nodes:
        logger.warning("No node data available for interaction graph")
        return None

    # Create the plot
    plt.figure(figsize=figsize)

    # Use a circular layout for the graph
    import math
    num_nodes = len(nodes)
    positions = {}

    for i, (agent_id, agent_name) in enumerate(nodes):
        angle = 2 * math.pi * i / num_nodes
        radius = 1.0
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        positions[agent_id] = (x, y)

    # Draw edges first (so they appear underneath nodes)
    if edges:
        # Normalize edge weights for visualization
        max_weight = max(edge[2] for edge in edges) if edges else 1.0

        for agent1_id, agent2_id, weight, edge_type in edges:
            if agent1_id in positions and agent2_id in positions:
                x1, y1 = positions[agent1_id]
                x2, y2 = positions[agent2_id]

                # Calculate edge width based on weight (normalize to reasonable range)
                width = 0.5 + 3.0 * (weight / max_weight) if max_weight > 0 else 0.5

                # Determine edge color based on type
                if edge_type == 'influence':
                    color = 'blue'
                    alpha = 0.7
                elif edge_type == 'message':
                    color = 'green'
                    alpha = 0.7
                else:  # combined or default
                    color = 'gray'
                    alpha = 0.5

                # Draw the edge
                plt.plot([x1, x2], [y1, y2],
                        color=color,
                        linewidth=width,
                        alpha=alpha,
                        zorder=1)

    # Draw nodes
    if nodes:
        # Normalize node sizes based on influence scores
        max_influence = 1.0
        if influence_data:
            influence_scores = []
            for agent_id, agent_name in nodes:
                if agent_id in influence_data:
                    influence_obj = influence_data[agent_id]
                    if isinstance(influence_obj, dict):
                        score = influence_obj.get('influence_score')
                        if score is not None:
                            influence_scores.append(score)
            if influence_scores:
                max_influence = max(influence_scores)

        for agent_id, agent_name in nodes:
            x, y = positions[agent_id]

            # Calculate node size based on influence score
            node_size = 300  # base size
            if agent_id in influence_data:
                influence_obj = influence_data[agent_id]
                if isinstance(influence_obj, dict):
                    score = influence_obj.get('influence_score')
                    if score is not None and max_influence > 0:
                        # Scale node size between 300 and 1200 based on influence
                        normalized_score = score / max_influence
                        node_size = 300 + 900 * normalized_score

            # Calculate radius based on node size (area scales with radius^2)
            # Base radius of 0.05 corresponds to node_size of 300
            radius = 0.05 * (node_size / 300) ** 0.5

            # Draw node as circle
            circle = plt.Circle((x, y), radius,
                              color='lightblue',
                              ec='navy',
                              linewidth=2,
                              zorder=3)
            plt.gca().add_patch(circle)

            # Add agent name below the node to avoid size constraints
            display_name = agent_name.split()[0] if ' ' in agent_name else agent_name
            # Further shorten if still too long
            if len(display_name) > 12:
                display_name = display_name[:12] + "."
            plt.text(x, y - radius - 0.02, display_name,  # Position below the node
                    ha='center', va='top',
                    fontsize=9, fontweight='bold',
                    zorder=4)

    # Customize the plot
    plt.title('Interaction Graph: Agent Communication and Influence Patterns',
              fontsize=14, fontweight='bold', pad=20)

    # Set equal aspect ratio and remove axes
    plt.axis('equal')
    plt.axis('off')

    # Add legend for edge types
    legend_elements = []
    if any(edge[3] == 'influence' for edge in edges):
        legend_elements.append(plt.Line2D([0], [0], color='blue', lw=3, label='Influence'))
    if any(edge[3] == 'message' for edge in edges):
        legend_elements.append(plt.Line2D([0], [0], color='green', lw=3, label='Message Volume'))
    if any(edge[3] == 'combined' for edge in edges):
        legend_elements.append(plt.Line2D([0], [0], color='gray', lw=3, label='Combined'))

    if legend_elements:
        plt.legend(handles=legend_elements, loc='upper right')

    # Add influence interpretation - moved to prevent overlap with graph
    plt.figtext(0.02, 0.01,
                "Node size represents influence score (larger = more influence)\n"
                "Edge width represents interaction strength (thicker = more interaction)\n"
                "Blue edges = influence-based, Green edges = message-volume-based",
                fontsize=9, style='italic',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))

    # Adjust layout with more bottom space to prevent overlap
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.20)  # Add more space at the bottom for labels

    # Ensure output directory exists
    import os
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

    logger.info(f"Interaction graph saved to {output_path}")
    return output_path


def _extract_trajectories_for_plotting(opinion_change_data: Dict[str, Any]) -> Dict[Tuple[str, str], List[Tuple[int, float]]]:
    """Extract trajectory data in a format suitable for plotting.

    Returns:
        Dictionary mapping (agent_id, agent_name) to list of (round, stance) tuples
    """
    trajectories = {}

    if not isinstance(opinion_change_data, dict):
        return trajectories

    # Handle different data formats
    if 'trajectories' in opinion_change_data:
        # Standard format from OpinionChangeResult.to_dict()
        traj_data = opinion_change_data['trajectories']
        if isinstance(traj_data, dict):
            for agent_id, points in traj_data.items():
                if not isinstance(points, list):
                    continue

                # Get agent name from first point if available
                agent_name = agent_id
                if points and isinstance(points[0], dict):
                    agent_name = points[0].get('agent_name', agent_id)

                # Extract (round, stance) tuples
                point_list = []
                for point in points:
                    if isinstance(point, dict):
                        round_num = point.get('round')
                        stance = point.get('stance')
                        if isinstance(round_num, int) and isinstance(stance, (int, float)):
                            point_list.append((round_num, float(stance)))

                if len(point_list) >= 2:  # Need at least 2 points to draw a line
                    trajectories[(agent_id, agent_name)] = point_list
    else:
        # Assume it's already in agent_id -> list format
        for agent_id, points in opinion_change_data.items():
            if not isinstance(points, list):
                continue

            # Get agent name from first point if available
            agent_name = agent_id
            if points and isinstance(points[0], dict):
                agent_name = points[0].get('agent_name', agent_id)

            # Extract (round, stance) tuples
            point_list = []
            for point in points:
                if isinstance(point, dict):
                    round_num = point.get('round')
                    stance = point.get('stance')
                    if isinstance(round_num, int) and isinstance(stance, (int, float)):
                        point_list.append((round_num, float(stance)))

            if len(point_list) >= 2:
                trajectories[(agent_id, agent_name)] = point_list

    return trajectories


def _extract_graph_data(
    influence_data: Dict[str, Any],
    message_activity_data: Optional[Dict] = None
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str, float, str]]]:
    """Extract node and edge data for the interaction graph.

    Returns:
        Tuple of (nodes, edges) where:
        - nodes: List of (agent_id, agent_name) tuples
        - edges: List of (agent1_id, agent2_id, weight, edge_type) tuples
                edge_type: 'influence', 'message', or 'combined'
    """
    nodes = []
    edges = []

    # Extract nodes from influence data (agents with influence scores)
    if isinstance(influence_data, dict):
        for agent_id, influence_obj in influence_data.items():
            if isinstance(influence_obj, dict):
                agent_name = influence_obj.get('agent_name', agent_id)
                nodes.append((agent_id, agent_name))

    # If no nodes from influence data, try to get them from message data
    if not nodes and message_activity_data:
        if isinstance(message_activity_data, dict):
            # Message activity data might be round -> {agent_id: count}
            # or agent_id -> {round: count} or similar
            agents_from_messages = set()
            if message_activity_data:
                # Try to extract agent IDs from the structure
                first_value = next(iter(message_activity_data.values()), None)
                if isinstance(first_value, dict):
                    # Format: round -> {agent_id: count}
                    for round_data in message_activity_data.values():
                        agents_from_messages.update(round_data.keys())
                else:
                    # Assume it's already agent_id -> something
                    agents_from_messages.update(message_activity_data.keys())

            for agent_id in agents_from_messages:
                nodes.append((agent_id, agent_id))  # Use ID as name if we don't have better info

    # Extract edges for influence data
    if isinstance(influence_data, dict):
        # Create a complete graph weighted by influence scores (simplified approach)
        # In a real implementation, this would be based on actual convergence data
        agent_list = [(agent_id, influence_obj.get('agent_name', agent_id))
                     for agent_id, influence_obj in influence_data.items()
                     if isinstance(influence_obj, dict)]

        # For demonstration, create edges based on influence score proximity
        # This is a simplified version - in reality, you'd use the actual convergence data
        for i, (agent1_id, agent1_name) in enumerate(agent_list):
            for j, (agent2_id, agent2_name) in enumerate(agent_list[i+1:], i+1):
                if agent1_id in influence_data and agent2_id in influence_data:
                    score1 = influence_data[agent1_id].get('influence_score', 0.0) or 0.0
                    score2 = influence_data[agent2_id].get('influence_score', 0.0) or 0.0
                    # Weight based on sum of influence scores (more influential agents have stronger connections)
                    weight = (score1 + score2) / 2.0
                    if weight > 0.01:  # Only show meaningful connections
                        edges.append((agent1_id, agent2_id, weight, 'influence'))

    # Extract edges for message activity data (if provided and different from influence)
    if message_activity_data and isinstance(message_activity_data, dict):
        # This would contain actual message exchange data
        # For now, we'll skip detailed message graph extraction since we don't have
        # the detailed message flow data in the current implementation
        pass

    return nodes, edges