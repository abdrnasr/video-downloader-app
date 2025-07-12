"use client"

import { useState,useRef,useEffect } from "react";
import Image from "next/image";
import useWebSocket from 'react-use-websocket';

// Unchaning constants
const maxAttemptCount = 5;

// These variables are initialized only on the client-side

let serverURL: string;
let websocketURL: string;
if (typeof window !== "undefined") {
  serverURL = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8000`;
  websocketURL = process.env.NEXT_PUBLIC_API_WEBSOCKET_URL || `ws://${window.location.hostname}:8000`;
}

/**
 * Checks if a given string is a valid HTTP or HTTPS URL.
 * 
 * @param string - The string to validate as a URL.
 * @returns {boolean} - Returns true if the string is a valid HTTP/HTTPS URL, otherwise false.
 */

function isValidHttpUrl(string: string) : boolean {
  let url;
  try {
    url = new URL(string);
  } catch(_) {
    return false;  
  }
  return url.protocol === "http:" || url.protocol === "https:";
}

interface ListItemProps {
    id: number;
    onRemove: (id: number) => void;
}

interface TaskIDResponse {
    task_id: string;
    status: string;
}

interface format{
  format_id: string;
  ext: string;
  vcodec: string;
  resolution: string;
  fps: number;
  filesize: string
}

interface VideoFormatsResponse {
  name: string;
  duration_string: string;
  formats: format[];
}

interface ThumbnailURLResponse {
  task_id: string;
  status: string;
  image_url?: string;
  error?: string;
}

interface CompletedTaskResponse {
  task_id: string;
  status: string;
  result?: VideoFormatsResponse; 
  error?: string;
}

export default function VideoDownloaderComp({id ,onRemove }: ListItemProps) {

      const [videoURL, setURL] = useState("");
      const [taskID,setTaskID] = useState("");
      const [retryFormatFetch,setRetryFormatFetch] = useState(false);
      const lastRequestedVideoURL = useRef("");

      const [loading, setLoading] = useState<boolean>(false);
      const [error, setError] = useState<string | null>(null);
    
      const attempts = useRef(0);
      const [videoFormatsData, setVideoFormatsData] = useState<CompletedTaskResponse>();

      const [thumbnailURL, setThumbnailURL] =useState<ThumbnailURLResponse>()

      const requestTaskID = async () => {
        // No requests should be made while loading
        if(loading){
          return;
        }

        // If the user had a task ID and the video URL has not changed, do nothing.
        // becuase it doesnt make sense to create a new task_id if the video URL has not changed
        if(taskID != "" && lastRequestedVideoURL.current == videoURL){
          // If for some reason the format data was not fetched, we retry.
          if(!videoFormatsData){
            fetchVideoData(taskID)
          }
          return;
        }
        lastRequestedVideoURL.current = videoURL;
        setLoading(true);
        setError(null);

        try {
          const response = await fetch(serverURL + "/video?url=" + videoURL);
          if (!response.ok) throw new Error(response.statusText);

          const result: TaskIDResponse = await response.json();
          setTaskID(result.task_id);
          fetchVideoData(result.task_id)

        } catch (err: any) {
          setError(err.message);
          setLoading(false);
        } 
      };

      const fetchVideoData = async (requestTaskID:string)=>{
        setLoading(true)
        const fetchVideoFormatData = async () => {
          try {
            const response = await fetch(serverURL + "/video/" + requestTaskID);
            if (!response.ok) {
              throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const jsonData: CompletedTaskResponse = await response.json();

            if(jsonData.status == "completed"){
              attempts.current = maxAttemptCount;
              return (jsonData)
            }else if(jsonData.status == "retry"){
              setLoading(false)
              setTaskID("")
              setError("There was an issue. Please try again.");
              attempts.current = maxAttemptCount;
            }
          } catch (error) {
            console.error('Error fetching data:', error);
          } 
          return null
        };

        attempts.current = 0;
        const intervalId = setInterval(async () => {
          
          if (attempts.current < maxAttemptCount && !videoFormatsData) {
            setVideoFormatsData(await fetchVideoFormatData() as CompletedTaskResponse);
          } else {
            clearInterval(intervalId); // Stop the interval after 3 attempts
            setLoading(false)
          }
          attempts.current++;
        }, 2000);
    
        return () => clearInterval(intervalId);
      }



      // Handles aquiring the thumbnail of the video
      useEffect(() => {
        if(!videoFormatsData){
          return
        }

        const fetchThumbnailPath = async () => {
          try {
            //console.log(serverURL + "/video/thumbnail/"+taskID);
            const response = await fetch(serverURL + "/video/thumbnail/"+taskID);
            if (!response.ok) {
              throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const jsonData: ThumbnailURLResponse = await response.json();
            setThumbnailURL(jsonData);
          } catch (error) {
            console.error('Error fetching data:', error);
          }
        }

        fetchThumbnailPath()
      }, [videoFormatsData]);

      const handleURLChange = (event:string|any) => {
        if(isValidHttpUrl(event.target.value)){
          setURL(event.target.value); 
        }else{
          setURL("");
        }
      };

    return (            
    <div className="card bg-base-200 shadow-xl">
        <div className="absolute top-3 right-3 !h-5 ">
            <button onClick={()=>onRemove(id)} className="btn btn-circle btn-sm font-cl bg-base-300 hover:bg-error">X</button>
        </div>
        <div className="card-body">
          <label className="ml-0.5" >URL:</label>
          <input onBlur={handleURLChange} type="text" placeholder="www.youtube.com/v=..." className="input input-bordered w-full"/>
          <div className="card-actions">
            {videoURL!=""?
            <button onClick={requestTaskID} className="btn btn-primary flex-grow">
            {loading?
            <span className="loading loading-spinner loading-xs"></span>:
            "Find Video"}
            </button>:
            <button className="btn flex-grow" disabled>Find Video</button>}
          </div>

          {
            error?
            <div role="alert" className="alert alert-error py-2 mt-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6 stroke-current"
              fill="none"
              viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
            :null
          }


          {
            videoFormatsData?.result?
            <ThumbnailComp 
            task_id={taskID}
            formatsResponse={videoFormatsData?.result as VideoFormatsResponse}
            imageURL={thumbnailURL?.image_url}
            />
            :null
          }
        </div>
    </div>)
}

interface VideoFormatToDownloadSubmittal{
  task_id:string,
  format_id:string
}

function ThumbnailComp({task_id,imageURL,formatsResponse}:{task_id:string,imageURL:string|undefined,formatsResponse:VideoFormatsResponse}){

  const [currentOptionID, setCurrentOptionID]=useState("")
  const [connect, setConnect] = useState(false);
  const [percentage, setPercentage] = useState(0);
  const [videoURL, setVideoURL] = useState("");


  useEffect(() => {
    if (videoURL != "") {
      handleDownload(serverURL+videoURL,formatsResponse.name);
    }
  }, [videoURL]);

  const handleSelectChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setCurrentOptionID((event.target.value));
  };

  const socketUrl = websocketURL+"/video/download";

  const {
    sendMessage,
    sendJsonMessage,
    lastMessage,
    lastJsonMessage,
    readyState,
    getWebSocket,
  } = useWebSocket(connect ? socketUrl : null, {
    onMessage: (message) => {
      try {
        const parsedMessage = JSON.parse(message.data);
    
        if (parsedMessage.progress !== undefined) {
          setPercentage(percentageToNumber(parsedMessage.progress));
        }else{
          if(parsedMessage.status == "completed"){
            setPercentage(100)
            setVideoURL(parsedMessage.URL)
          }
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    },
    shouldReconnect: (closeEvent) => false,
  });

  useEffect(() => {
    setCurrentOptionID("")
  }, [imageURL]);

  const handleButtonClick = () => {
    setConnect(true)
    sendJsonMessage({"task_id":task_id,"format":currentOptionID})
  };

  if(!imageURL || imageURL == ""){
    return(
      <div className="flex justify-center">
        <span className="loading loading-dots loading-lg text-primary"></span>
      </div>
    )
  }
  const fullUrl = serverURL + imageURL
  return(
    <div className="h-fit lg:flex lg:justify-between bg-base-300 shadow-2xs rounded-lg">
      <div className="p-2 flex-1 flex-col">
        <p className="text-primary">Video Info:</p>
        <p className="text-primary">Title: 
          <span className="ml-1 text-base-content">{formatsResponse.name}</span>
        </p>
        <p className="text-primary">Duration: 
          <span className="ml-1 text-base-content">{formatsResponse.duration_string}</span>
        </p>
        <p className="text-primary">Available Formats: 
        </p>
        <select value={currentOptionID} onChange={handleSelectChange} className="select select-bordered w-full mt-2 self-stretch">
        <option value="" disabled>Select Format</option>
          {
          formatsResponse.formats.filter(
            (formatItem : format)=> {
              return (
                !formatItem.vcodec.includes("vp") && 
                formatItem.resolution !=("audio only") &&
                formatItem.fps>10)
            }).map(
            (formatItem:format)=> <option key={formatItem.format_id} value={formatItem.format_id} >
              {formatItem.resolution +" "+
              formatItem.fps    +"FPS "+
              formatItem.vcodec +" "+
              formatItem.ext}
              </option>
          )}

        </select>
        {
          currentOptionID!=""?
          <button disabled={connect} onClick={handleButtonClick} className="btn btn-primary w-full mt-2 self">
            {
            !connect ?"Download Selected Format":
            ((percentage < 99.9)?
            <progress className="progress progress-primary w-56" value={percentage} max="100"></progress>:
            "Complete"
            )
            }
          </button>
          :null
        }
      </div>
      
      <Image
      className=""
      src={fullUrl as string}
      alt="Thumbnail"
      width={400}
      height={400}
      style={{ objectFit: "scale-down",padding:"10px",justifySelf:"center" }}
      />
      
    </div>
  )

}
function percentageToNumber(percentage: string): number {
  return parseFloat(percentage.trim().replace('%', ''));
}

const handleDownload = async (itemUrl: string, videoName: string) => {
  try {
    const response = await fetch(itemUrl);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    // Extract the extension from the URL (e.g., .mp4)
    const extension = itemUrl.substring(itemUrl.lastIndexOf('.')) || '.mp4';

    // Build the full filename with extension
    const fullName = `${videoName}${extension}`;

    const a = document.createElement('a');
    a.href = url;
    a.download = fullName; // Set correct download name with extension
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error downloading the video:', error);
  }
};