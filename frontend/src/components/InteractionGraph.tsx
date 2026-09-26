import React from 'react'
import { getAgentColor } from './MessageCard'

interface InteractionGraphProps {
  nodes: Array<{ agent_id: string; message_count: number; influence_score: number | null }>
  edges: Array<{ source: string; target: string; weight: number; kind: string }>
}

function hexWithAlpha(hex: string, alphaHex: string): string {
  const clean = hex.replace('#', '')
  const full = clean.length === 3 ? clean.split('').map(c => c + c).join('') : clean
  return `#${full}${alphaHex}`
}

const InteractionGraph: React.FC<InteractionGraphProps> = ({ nodes, edges }) => {
  if (!nodes.length) {
    return (
      <div className="text-center py-12" role="status">
        <div className="space-y-4">
          <div aria-hidden="true" className="h-12 w-12 border-4 border-climate-blue border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-lg font-medium text-climate-blue">No interaction data available</p>
          <p className="text-sm text-gray-500">
            Start a discussion to generate interaction insights.
          </p>
        </div>
      </div>
    )
  }

  const width = 420
  const height = 420
  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(width, height) * 0.35

  // Position nodes in a circle
  const positionedNodes = nodes.map((node, index) => {
    const angle = (index / nodes.length) * 2 * Math.PI - Math.PI / 2
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    }
  })

  // Get agent display name
  const getAgentName = (agentId: string): string => {
    return agentId
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900 mb-3 bg-clip-text text-transparent bg-gradient-to-r from-climate-blue to-climate-green">
          Interaction Graph
        </h2>
        <p className="text-sm text-gray-600 max-w-xl mx-auto">
          Visualizes relationships and interaction strength between agents
        </p>
      </div>

      <div className="relative w-full max-w-[420px] h-[420px] mx-auto" role="img" aria-label={`Interaction graph with ${nodes.length} agents and ${edges.length} connections`}>
        <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full" aria-hidden="true">
          <defs>
            <radialGradient id="graphGradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="white" />
              <stop offset="100%" stopColor="#f8fafc" />
            </radialGradient>
          </defs>
          <circle cx={centerX} cy={centerY} r={radius + 20} fill="url(#graphGradient)" />

          {/* Draw edges with enhanced styling */}
          {edges.map((edge, index) => {
            const sourceNode = positionedNodes.find(n => n.agent_id === edge.source)
            const targetNode = positionedNodes.find(n => n.agent_id === edge.target)

            if (!sourceNode || !targetNode) return null

            // Calculate edge properties based on weight
            const opacity = Math.min(0.8, Math.max(0.2, edge.weight / 15))
            const strokeWidth = Math.max(2, Math.min(8, edge.weight / 3))

            // Determine edge color based on weight (lighter for weaker, stronger for stronger)
            const edgeIntensity = Math.min(1, edge.weight / 10)
            const edgeColor = `hsl(210, 80%, ${30 + Math.round(edgeIntensity * 40)}%)`

            return (
              <line
                key={`${edge.source}-${edge.target}-${index}`}
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                stroke={edgeColor}
                strokeWidth={strokeWidth}
                opacity={opacity}
                strokeDasharray={edge.weight > 5 ? undefined : '4,2'}
              />
            )
          })}

          {/* Draw nodes with enhanced styling */}
          {positionedNodes.map((node) => {
            const agentName = getAgentName(node.agent_id)
            const color = getAgentColor(node.agent_id)
            const influencePercentage = (node.influence_score ?? 0) * 100

            return (
              <g key={node.agent_id}>
                {/* Node outer glow */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={28}
                  fill={color}
                  fillOpacity={0.15}
                />

                {/* Node circle with subtle gradient effect */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={24}
                  fill={color}
                />

                {/* Node highlight */}
                <circle
                  cx={node.x - 6}
                  cy={node.y - 6}
                  r={8}
                  fill="white"
                  fillOpacity={0.3}
                />

                {/* Message count badge */}
                <g>
                  <rect
                    x={node.x - 22}
                    y={node.y - 10}
                    width={44}
                    height={20}
                    rx={10}
                    fill="rgba(0, 0, 0, 0.4)"
                  />
                  <text
                    x={node.x}
                    y={node.y + 4}
                    textAnchor="middle"
                    fill="white"
                    fontSize={12}
                    fontWeight={500}
                  >
                    {node.message_count}
                  </text>
                </g>

                {/* Agent label */}
                <g>
                  <rect
                    x={node.x - 30}
                    y={node.y + 28}
                    width={60}
                    height={20}
                    rx={10}
                    fill={hexWithAlpha(color, 'DD')}
                  />
                  <text
                    x={node.x}
                    y={node.y + 42}
                    textAnchor="middle"
                    fill="white"
                    fontSize={10}
                    fontWeight={500}
                  >
                    {agentName.length > 12 ? `${agentName.slice(0, 11)}…` : agentName}
                  </text>
                </g>

                {/* Influence score */}
                <g>
                  <rect
                    x={node.x - 25}
                    y={node.y + 52}
                    width={50}
                    height={6}
                    rx={3}
                    fill="#e5e7eb"
                  />
                  <rect
                    x={node.x - 25}
                    y={node.y + 52}
                    width={Math.max(0, Math.min(50, (influencePercentage / 100) * 50))}
                    height={6}
                    rx={3}
                    fill={color}
                  />
                  <text
                    x={node.x}
                    y={node.y + 68}
                    textAnchor="middle"
                    fill="#6b7280"
                    fontSize={10}
                  >
                    {influencePercentage.toFixed(0)}%
                  </text>
                </g>
              </g>
            )
          })}
        </svg>
      </div>

      {/* Screen-reader / text fallback for the visual graph */}
      <ul className="sr-only">
        {positionedNodes.map((node) => (
          <li key={node.agent_id}>
            {getAgentName(node.agent_id)}: {node.message_count} messages,{' '}
            {((node.influence_score ?? 0) * 100).toFixed(1)}% influence
          </li>
        ))}
      </ul>

      <div className="mt-6 text-center text-sm text-gray-500 space-y-2">
        <p>
          <span className="font-medium">Node size</span> represents message volume and influence
        </p>
        <p>
          <span className="font-medium">Edge thickness</span> shows interaction strength<br />
          <span className="font-medium">Node position</span> arranged in circular layout
        </p>
        <p className="mt-2 text-xs text-gray-400">
          Influence scores normalized to sum 100% across all agents
        </p>
      </div>
    </div>
  )
}

export default InteractionGraph
