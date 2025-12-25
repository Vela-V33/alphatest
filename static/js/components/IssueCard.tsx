import React from 'react';
import { MessageSquare, Send, Share2, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { Issue } from './types';

interface IssueCardProps {
  issue: Issue;
  onShare: (platform: string, issue: Issue) => void;
}

const IssueCard: React.FC<IssueCardProps> = ({ issue, onShare }) => {
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
    <div className="glass-card p-4 hover:bg-white/5 transition-all duration-300 hover:scale-[1.02] group">
      {/* Screenshot Thumbnail */}
      {issue.screenshot && (
        <img
          src={issue.screenshot}
          alt="Issue screenshot"
          className="w-full h-20 object-cover rounded-lg border border-white/10 mb-3"
        />
      )}

      {/* Severity Badge */}
      <div className="flex items-center justify-between mb-2">
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded border text-xs font-light ${getSeverityColor(issue.severity)}`}>
          {getSeverityIcon(issue.severity)}
          {issue.severity}
        </span>
        <span className="text-xs text-slate-500 font-light">Step #{issue.step}</span>
      </div>

      {/* Title */}
      <h3 className="text-sm text-white font-light mb-2 line-clamp-2">{issue.title}</h3>

      {/* Description */}
      <p className="text-xs text-slate-400 font-light mb-3 line-clamp-2">{issue.description}</p>

      {/* Share Actions */}
      <div className="flex items-center gap-2 pt-3 border-t border-white/10">
        <button
          onClick={() => onShare('slack', issue)}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 rounded transition-all duration-300 text-xs text-slate-300"
          title="Share to Slack"
        >
          <MessageSquare className="w-3 h-3" />
          Slack
        </button>
        <button
          onClick={() => onShare('teams', issue)}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 rounded transition-all duration-300 text-xs text-slate-300"
          title="Share to Teams"
        >
          <Send className="w-3 h-3" />
          Teams
        </button>
        <button
          onClick={() => onShare('whatsapp', issue)}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 rounded transition-all duration-300 text-xs text-slate-300"
          title="Share to WhatsApp"
        >
          <Share2 className="w-3 h-3" />
          WhatsApp
        </button>
      </div>
    </div>
  );
};

export default IssueCard;
