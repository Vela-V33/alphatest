import React, { useState } from 'react';
import { X } from 'lucide-react';

interface InviteModalProps {
  onClose: () => void;
  onInvite: (email: string, role: 'admin' | 'viewer') => void;
}

const InviteModal: React.FC<InviteModalProps> = ({ onClose, onInvite }) => {
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'viewer'>('viewer');

  const handleSubmit = () => {
    if (inviteEmail) {
      onInvite(inviteEmail, inviteRole);
      setInviteEmail('');
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="glass-card max-w-md w-full p-6 animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">Invite Collaborator</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded transition-colors duration-300"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-slate-300 font-light mb-2">Email Address</label>
            <input
              type="email"
              placeholder="colleague@company.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="input-glass w-full px-4 py-3 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-300 font-light mb-2">Role</label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as 'admin' | 'viewer')}
              className="input-glass w-full px-4 py-3 text-sm"
            >
              <option value="viewer">Viewer - Can view issues and reports</option>
              <option value="admin">Admin - Can manage issues and collaborators</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <button onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!inviteEmail}
              className="btn-primary flex-1"
            >
              Send Invitation
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InviteModal;
