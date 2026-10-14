import React from 'react';
import { SchematicMap } from '../map/SchematicMap';

export const Screen1NetworkMap: React.FC = () => {
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      <SchematicMap />
    </div>
  );
};
