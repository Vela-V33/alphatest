import React from 'react';
import IssueCard from './IssueCard';
import { Issue } from './types';

interface IssueBucketsProps {
  issues: Issue[];
  onShare: (platform: string, issue: Issue) => void;
}

const IssueBuckets: React.FC<IssueBucketsProps> = ({ issues, onShare }) => {
  // Group issues by category
  const issuesByCategory = {
    'ui-ux': issues.filter(i => i.category === 'ui-ux'),
    'security': issues.filter(i => i.category === 'security'),
    'logic': issues.filter(i => i.category === 'logic'),
  };

  const CategoryColumn: React.FC<{
    title: string;
    color: string;
    issues: Issue[];
    category: 'ui-ux' | 'security' | 'logic';
  }> = ({ title, color, issues: categoryIssues, category }) => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${color}`}></div>
          {title}
        </h2>
        <span className="text-xs text-slate-400 font-light">
          {categoryIssues.length} issues
        </span>
      </div>

      <div className="space-y-3">
        {categoryIssues.map((issue) => (
          <IssueCard key={issue.id} issue={issue} onShare={onShare} />
        ))}
        {categoryIssues.length === 0 && (
          <div className="glass-card p-6 text-center">
            <p className="text-sm text-slate-500 font-light">No {title} issues found</p>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <CategoryColumn
        title="UI/UX"
        color="bg-blue-400"
        issues={issuesByCategory['ui-ux']}
        category="ui-ux"
      />
      <CategoryColumn
        title="Security"
        color="bg-red-400"
        issues={issuesByCategory['security']}
        category="security"
      />
      <CategoryColumn
        title="Logic"
        color="bg-yellow-400"
        issues={issuesByCategory['logic']}
        category="logic"
      />
    </div>
  );
};

export default IssueBuckets;
