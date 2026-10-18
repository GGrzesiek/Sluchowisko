import { Callout, FactGrid, PhotoFigure, Prose, StoryTimeline } from "./Article";
import type { StoryBlock, StoryPhoto } from "../types";

const IMAGE_HEIGHT = 200;

export function StoryBlocks({ blocks, photos }: { blocks: StoryBlock[]; photos: StoryPhoto[] }) {
  return (
    <div className="flex flex-col gap-5">
      {blocks.map((block, i) => {
        switch (block.type) {
          case "paragraph":
            return <Prose key={i}>{block.text}</Prose>;
          case "image": {
            const photo = photos[block.photo];
            return photo ? (
              <PhotoFigure
                key={i}
                src={photo.src}
                alt={photo.alt}
                year={photo.year}
                caption={photo.caption}
                height={IMAGE_HEIGHT}
              />
            ) : null;
          }
          case "facts":
            return <FactGrid key={i} facts={block.items} />;
          case "callout":
            return (
              <Callout key={i} title={block.title}>
                {block.text}
              </Callout>
            );
          case "timeline":
            return <StoryTimeline key={i} events={block.items} />;
        }
      })}
    </div>
  );
}
