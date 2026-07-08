import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TagsPanel from './TagsPanel';

describe('TagsPanel', () => {
  it('renders empty state when no tags', () => {
    render(<TagsPanel tags={[]} />);
    expect(screen.getByTestId('tags-panel')).toBeInTheDocument();
    expect(screen.getByText('No tags.')).toBeInTheDocument();
  });

  it('renders empty state when tags is undefined', () => {
    render(<TagsPanel tags={undefined} />);
    expect(screen.getByTestId('tags-panel')).toBeInTheDocument();
    expect(screen.getByText('No tags.')).toBeInTheDocument();
  });

  it('renders category rows with values and counts', () => {
    const tags = [
      {
        category: 'Sentiment',
        category_id: 'cat1',
        values: ['Positive', 'Neutral'],
        node_count: 5,
      },
      {
        category: 'Intent',
        category_id: 'cat2',
        values: ['Question'],
        node_count: 1,
      },
    ];
    render(<TagsPanel tags={tags} />);

    expect(screen.getByTestId('tags-panel')).toBeInTheDocument();
    const rows = screen.getAllByTestId('tag-category-row');
    expect(rows).toHaveLength(2);

    expect(screen.getByText('Sentiment')).toBeInTheDocument();
    expect(screen.getByText('Intent')).toBeInTheDocument();
    expect(screen.getByText('5 nodes')).toBeInTheDocument();
    expect(screen.getByText('1 node')).toBeInTheDocument();
    expect(screen.getByText('Positive')).toBeInTheDocument();
    expect(screen.getByText('Neutral')).toBeInTheDocument();
    expect(screen.getByText('Question')).toBeInTheDocument();
  });

  it('uses category_id as key when available', () => {
    const tags = [
      {
        category: 'Sentiment',
        category_id: 'cat1',
        values: [],
        node_count: 2,
      },
    ];
    render(<TagsPanel tags={tags} />);
    expect(screen.getByText('Sentiment')).toBeInTheDocument();
  });

  it('uses category name as key fallback when category_id unavailable', () => {
    const tags = [
      {
        category: 'Priority',
        values: [],
        node_count: 3,
      },
    ];
    render(<TagsPanel tags={tags} />);
    expect(screen.getByText('Priority')).toBeInTheDocument();
  });
});
