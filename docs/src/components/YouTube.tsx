import type {ReactNode} from 'react';

interface YouTubeProps {
  id: string;
  title?: string;
}

export default function YouTube({id, title = 'Video'}: YouTubeProps): ReactNode {
  return (
    <div style={{textAlign: 'center', margin: '1.5rem 0'}}>
      <iframe
        width="100%"
        height="400"
        style={{maxWidth: 640, borderRadius: 8}}
        src={`https://www.youtube.com/embed/${id}`}
        title={title}
        frameBorder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    </div>
  );
}
