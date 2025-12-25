import React from 'react';
import { Search, Download, Save, MessageSquare, Send, Share2, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { Issue } from './types';

interface IssueRegisterProps {
  issues: Issue[];
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  filterSeverity: string;
  setFilterSeverity: (severity: string) => void;
  filterCategory: string;
  setFilterCategory: (category: string) => void;
  onShare: (platform: string, issue: Issue) => void;
  onExportPDF: () => void;
  onSave: () => void;
}

const IssueRegister: React.FC<IssueRegisterProps> = ({
  issues,
  searchQuery,
  setSearchQuery,
  filterSeverity,
  setFilterSeverity,
  filterCategory,
  setFilterCategory,
  onShare,
  onExportPDF,
  onSave
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/30 text-red-400';
      case 'high':
        return 'bg-orange-500/10 border-orange-500/30 text-orange-400';
      case 'medium':
        return 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400';
      case 'low':
        return 'bg-slate-500/10 border-slate-500/30 text-slate-400';
      default:
        return 'bg-slate-500/10 border-slate-500/30 text-slate-400';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-3 h-3" />;
      case 'high':
        return <AlertCircle className="w-3 h-3" />;
      case 'medium':
        return <Info className="w-3 h-3" />;
      default:
        return <Info className="w-3 h-3" />;
    }
  };

  return (
    <div className="glass-card p-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
        <h2 className="text-lg font-semibold text-white">Issue Register</h2>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Search */}
          <div className="relative flex-1 md:flex-none">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search issues..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-glass pl-10 pr-4 py-2 w-full md:w-64 text-sm"
            />
          </div>

          {/* Filters */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="input-glass px-3 py-2 text-sm"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="input-glass px-3 py-2 text-sm"
          >
            <option value="all">All Categories</option>
            <option value="ui-ux">UI/UX</option>
            <option value="security">Security</option>
            <option value="logic">Logic</option>
          </select>

          {/* Actions */}
          <button onClick={onSave} className="btn-secondary flex items-center gap-2 text-sm">
            <Save className="w-4 h-4" />
            <span className="hidden md:inline">Save</span>
          </button>

          <button onClick={onExportPDF} className="btn-primary flex items-center gap-2 text-sm">
            <Download className="w-4 h-4" />
            <span className="hidden md:inline">Export PDF</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Issue
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden md:table-cell">
                Category
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Severity
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden lg:table-cell">
                Step
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden lg:table-cell">
                Status
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue) => (
              <tr
                key={issue.id}
                className="border-b border-white/5 hover:bg-white/5 transition-colors duration-300"
              >
                <td className="py-4 px-4">
                  <div className="flex items-start gap-3">
                    {issue.screenshot && (
                      <img
                        src={issue.screenshot}
                        alt="Issue screenshot"
                        className="w-12 h-8 object-cover rounded border border-white/10 hidden sm:block"
                      />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm text-white font-light line-clamp-1">{issue.title}</p>
                      <p className="text-xs text-slate-400 font-light mt-1 line-clamp-1">
                        {issue.description}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="py-4 px-4 hidden md:table-cell">
                  <span className="text-xs text-slate-300 font-light uppercase tracking-wider">
                    {issue.category.replace('-', '/')}
                  </span>
                </td>
                <td className="py-4 px-4">
                  <span className={`inline-flex items-center gap-1 px-2 py-1 rounded border text-xs font-light ${getSeverityColor(issue.severity)}`}>
                    {getSeverityIcon(issue.severity)}
                    <span className="hidden sm:inline">{issue.severity}</span>
                  </span>
                </td>
                <td className="py-4 px-4 hidden lg:table-cell">
                  <span className="text-sm text-slate-300 font-light">#{issue.step}</span>
                </td>
                <td className="py-4 px-4 hidden lg:table-cell">
                  <span
                    className={`inline-flex px-2 py-1 rounded text-xs font-light ${
                      issue.status === 'resolved'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : issue.status === 'in-progress'
                        ? 'bg-yellow-500/10 text-yellow-400'
                        : 'bg-slate-500/10 text-slate-400'
                    }`}
                  >
                    {issue.status}
                  </span>
                </td>
                <td className="py-4 px-4">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onShare('slack', issue)}
                      className="p-2 hover:bg-white/10 rounded transition-colors duration-300"
                      title="Share to Slack"
                    >
                      <MessageSquare className="w-4 h-4 text-slate-400" />
                    </button>
                    <button
                      onClick={() => onShare('teams', issue)}
                      className="p-2 hover:bg-white/10 rounded transition-colors duration-300 hidden sm:block"
                      title="Share to Teams"
                    >
                      <Send className="w-4 h-4 text-slate-400" />
                    </button>
                    <button
                      onClick={() => onShare('whatsapp', issue)}
                      className="p-2 hover:bg-white/10 rounded transition-colors duration-300"
                      title="Share to WhatsApp"
                    >
                      <Share2 className="w-4 h-4 text-slate-400" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {issues.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-400 font-light">No issues match your search criteria</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default IssueRegister;
