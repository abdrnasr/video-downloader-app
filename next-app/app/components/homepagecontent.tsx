"use client"
import { useEffect, useState } from "react";
import VideoDownloaderComp from "./videodownloader";

let uniqueIdCounter = 0;
// Generate a unique ID that can be used as a key to the map function.
const generateId = () => {
    return uniqueIdCounter++;
  };
  

export default function HomePageContent(){

  // Remove the item with the specified ID.
  // This will allow the user to remove existing "download" widgets.
  const removeItem = (id: number) => {
    setVideosToDownload(
      (prevItems) => prevItems.filter((item) => item !== id)
    );
  };
  // This will allow the user to add new "download" widgets
  const addButtonClick = ()=>{
    setVideosToDownload([...videosToDownload, generateId()])
  }
  
  // Creates the first download widget only after the first render.
  useEffect(() => {
    addButtonClick()
  }
  , [])

  // Holds the ID of the "download" widgets, which allow the user to download videos.
  const [videosToDownload, setVideosToDownload]=useState<number[]>([])
  
  // Creates the TSX of containg all the widgets to download a video
  const videosCards = videosToDownload.map(video=>{ return <VideoDownloaderComp onRemove={removeItem} key={video} id={video}/>}) 
    return(
        <section className="mx-[2.5vw] sm:mx-[10vw] p-5 shadow-[0px_1px_1px_0px] shadow-shadowcast flex-grow-[2] flex flex-col items-center ">
        <div className="flex flex-col space-y-3.5 w-full">
            {videosCards}
        </div>
        <button onClick={addButtonClick} className="btn btn-primary mt-5 px-5 w-full max-w-[200px]">Add</button>
        </section>
    )

}

