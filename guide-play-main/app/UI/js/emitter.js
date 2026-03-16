import * as postme from "./postme.js";

// const postme = require('./postme.js');
const { ParentHandshake, WorkerMessenger } = postme;

console.log('emitter.js loaded', postme);
console.log('emitter.js loaded', ParentHandshake);
console.log('emitter.js loaded', WorkerMessenger);


// const worker = new Worker('js/emitter-worker.js');

// const messenger = new WorkerMessenger({ worker });

// ParentHandshake(messenger).then((connection) => {
//   const remoteHandle = connection.remoteHandle();

//   // Call methods on the worker and get the result as a promise
//   remoteHandle.call('sum', 3, 4).then((result) => {
//     console.log(result); // 7
//   });

//   // Listen for a specific custom event from the worker
//   remoteHandle.addEventListener('ping', (payload) => {
//     console.log(payload) // 'Oh, hi!'
//   });
// });

// console.log('emitter.js loaded');