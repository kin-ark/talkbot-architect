import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import FlowCanvas from './FlowCanvas';

beforeEach(() => {
  global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
});

const SUMMARY_WITH_TAGS = {
  components: [
    {
      uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
      nodes: {
        a1: {
          uuid: 'a1', label: 'Greet', node_type: 'talk',
          tags: [
            { category: 'disposition', value: 'positive' },
            { category: 'feedback', value: 'helpful' },
          ],
          branches: [],
        },
      },
    },
  ],
  knowledge_bases: [],
};

const SUMMARY_WITHOUT_TAGS = {
  components: [
    {
      uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
      nodes: {
        a1: { uuid: 'a1', label: 'Greet', node_type: 'talk', tags: [], branches: [] },
      },
    },
  ],
  knowledge_bases: [],
};

describe('FlowCanvas tag rendering', () => {
  it('renders tag chips when node has tags', () => {
    render(<FlowCanvas summary={SUMMARY_WITH_TAGS} onSelectNode={() => {}} />);
    // Click to expand the component so the node is visible
    const compButton = screen.getByText('Greeting');
    fireEvent.click(compButton);

    // Check that tags are rendered
    const tags = screen.getAllByTestId('node-tag');
    expect(tags).toHaveLength(2);
    expect(tags[0]).toHaveTextContent('positive');
    expect(tags[1]).toHaveTextContent('helpful');
  });

  it('renders no tags when node has empty tags array', () => {
    render(<FlowCanvas summary={SUMMARY_WITHOUT_TAGS} onSelectNode={() => {}} />);
    // Click to expand the component so the node is visible
    const compButton = screen.getByText('Greeting');
    fireEvent.click(compButton);

    // Check that no tags are rendered
    const tags = screen.queryAllByTestId('node-tag');
    expect(tags).toHaveLength(0);
  });

  it('truncates tags to 3 and shows overflow count', () => {
    const summaryManyTags = {
      components: [
        {
          uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
          nodes: {
            a1: {
              uuid: 'a1', label: 'Greet', node_type: 'talk',
              tags: [
                { category: 'disposition', value: 'positive' },
                { category: 'feedback', value: 'helpful' },
                { category: 'quality', value: 'good' },
                { category: 'extra', value: 'tag4' },
                { category: 'another', value: 'tag5' },
              ],
              branches: [],
            },
          },
        },
      ],
      knowledge_bases: [],
    };
    render(<FlowCanvas summary={summaryManyTags} onSelectNode={() => {}} />);
    // Click to expand the component so the node is visible
    const compButton = screen.getByText('Greeting');
    fireEvent.click(compButton);

    // Check that only 3 tags are rendered
    const tags = screen.getAllByTestId('node-tag');
    expect(tags).toHaveLength(3);
    // Check for overflow text
    expect(screen.getByText('+2')).toBeInTheDocument();
  });
});
