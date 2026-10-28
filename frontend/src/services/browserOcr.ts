import {createWorker,OEM} from 'tesseract.js';

export async function extractTextInBrowser(file:File,onProgress:(progress:number)=>void):Promise<string>{
  const worker=await createWorker('eng',OEM.LSTM_ONLY,{logger:message=>{
    if(message.status==='recognizing text'&&typeof message.progress==='number')onProgress(message.progress);
  }});
  try{
    const {data}=await worker.recognize(file);
    return data.text.trim();
  }finally{
    await worker.terminate();
  }
}
