import React, { useState, useEffect } from 'react';
import {
  UserPlus,
  Search,
  Download,
  Save,
  Filter
} from 'lucide-react';
import CollaboratorBar from './CollaboratorBar';
import IssueBuckets from './IssueBuckets';
import IssueRegister from './IssueRegister';
import InviteModal from './InviteModal';
import { Collaborator, Issue } from './types';

const CollaborationDashboard: React.FC = () => {
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [projectId, setProjectId] = useState<string>('');
  const [projectName, setProjectName] = useState<string>('');

  useEffect(() => {
    // Get project ID from URL
    const pathParts = window.location.pathname.split('/');
    const id = pathParts[pathParts.indexOf('project') + 1];
    setProjectId(id);

    // Fetch project data and issues
    fetchProjectData(id);
  }, []);

  const fetchProjectData = async (id: string) => {
    try {
      // Fetch collaborators
      const collabResponse = await fetch(`/api/project/${id}/collaborators`);
      if (collabResponse.ok) {
        const collabData = await collabResponse.json();
        setCollaborators(collabData.collaborators || []);
      }

      // Fetch issues
      const issuesResponse = await fetch(`/api/project/${id}/issues`);
      if (issuesResponse.ok) {
        const issuesData = await issuesResponse.json();
        setIssues(issuesData.issues || []);
        setProjectName(issuesData.project_name || 'Project');
      }
    } catch (error) {
      console.error('Error fetching project data:', error);
    }
  };

  const handleInvite = async (email: string, role: 'admin' | 'viewer') => {
    try {
      const response = await fetch(`/api/project/${projectId}/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role })
      });

      if (response.ok) {
        const data = await response.json();
        setCollaborators([...collaborators, data.collaborator]);
        setShowInviteModal(false);
      }
    } catch (error) {
      console.error('Error inviting collaborator:', error);
    }
  };

  const handleShare = async (platform: string, issue: Issue) => {
    const message = `Issue: ${issue.title}\nSeverity: ${issue.severity.toUpperCase()}\nStep: ${issue.step}\n\n${issue.description}`;

    switch (platform) {
      case 'slack':
        // Slack webhook integration
        console.log('Share to Slack:', message);
        break;
      case 'teams':
        // Teams webhook integration
        console.log('Share to Teams:', message);
        break;
      case 'whatsapp':
        const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;
        window.open(whatsappUrl, '_blank');
        break;
    }
  };

  const exportPDF = async () => {
    try {
      const response = await fetch(`/api/project/${projectId}/export-issues`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issues: filteredIssues })
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `issues-${projectId}-${Date.now()}.pdf`;
        a.click();
      }
    } catch (error) {
      console.error('Error exporting PDF:', error);
    }
  };

  const saveProject = async () => {
    try {
      await fetch(`/api/project/${projectId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      alert('Project saved successfully');
    } catch (error) {
      console.error('Error saving project:', error);
    }
  };

  // Filter issues
  const filteredIssues = issues.filter(issue => {
    const matchesSearch = issue.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         issue.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSeverity = filterSeverity === 'all' || issue.severity === filterSeverity;
    const matchesCategory = filterCategory === 'all' || issue.category === filterCategory;
    return matchesSearch && matchesSeverity && matchesCategory;
  });

  const highPriorityCount = issues.filter(i =>
    i.severity === 'critical' || i.severity === 'high'
  ).length;

  const inProgressCount = issues.filter(i =>
    i.status === 'in-progress'
  ).length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 relative">
      {/* Technical Grid Overlay */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      />

      {/* Main Content */}
      <div className="relative z-10 max-w-[1800px] mx-auto p-6 space-y-6">

        {/* Header with Collaborator Bar */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-semibold text-white mb-1">Issue Triage</h1>
              <p className="text-sm text-slate-400 font-light">
                Automated UAT Test Run • Project: {projectName}
              </p>
            </div>

            <CollaboratorBar
              collaborators={collaborators}
              onInviteClick={() => setShowInviteModal(true)}
            />
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="stat-card">
              <div className="text-2xl font-semibold text-white">{issues.length}</div>
              <div className="text-xs text-slate-400 mt-1 font-light">Total Issues</div>
            </div>
            <div className="stat-card">
              <div className="text-2xl font-semibold text-red-400">{highPriorityCount}</div>
              <div className="text-xs text-slate-400 mt-1 font-light">High Priority</div>
            </div>
            <div className="stat-card">
              <div className="text-2xl font-semibold text-yellow-400">{inProgressCount}</div>
              <div className="text-xs text-slate-400 mt-1 font-light">In Progress</div>
            </div>
            <div className="stat-card">
              <div className="text-2xl font-semibold text-emerald-400">{collaborators.length}</div>
              <div className="text-xs text-slate-400 mt-1 font-light">Team Members</div>
            </div>
          </div>
        </div>

        {/* Issue Buckets */}
        <IssueBuckets
          issues={filteredIssues}
          onShare={handleShare}
        />

        {/* Issue Register */}
        <IssueRegister
          issues={filteredIssues}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          filterSeverity={filterSeverity}
          setFilterSeverity={setFilterSeverity}
          filterCategory={filterCategory}
          setFilterCategory={setFilterCategory}
          onShare={handleShare}
          onExportPDF={exportPDF}
          onSave={saveProject}
        />
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <InviteModal
          onClose={() => setShowInviteModal(false)}
          onInvite={handleInvite}
        />
      )}
    </div>
  );
};

export default CollaborationDashboard;
