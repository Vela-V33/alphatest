import React from 'react';
import { UserPlus } from 'lucide-react';
import { Collaborator } from './types';

interface CollaboratorBarProps {
  collaborators: Collaborator[];
  onInviteClick: () => void;
}

const CollaboratorBar: React.FC<CollaboratorBarProps> = ({ collaborators, onInviteClick }) => {
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-3">
        <div className="flex -space-x-3">
          {collaborators.map((collab) => (
            <div
              key={collab.id}
              className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600
                       border-2 border-slate-900 flex items-center justify-center text-white text-xs font-semibold
                       hover:scale-110 transition-transform duration-300 cursor-pointer relative group"
              title={`${collab.name} (${collab.role})`}
            >
              {collab.avatar || getInitials(collab.name)}

              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 hidden group-hover:block">
                <div className="glass-card px-3 py-2 whitespace-nowrap">
                  <p className="text-xs text-white font-medium">{collab.name}</p>
                  <p className="text-xs text-slate-400">{collab.email}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Invite Button */}
        <button
          onClick={onInviteClick}
          className="btn-primary flex items-center gap-2 text-sm px-4 py-2"
        >
          <UserPlus className="w-4 h-4" />
          Invite
        </button>
      </div>
    </div>
  );
};

export default CollaboratorBar;
